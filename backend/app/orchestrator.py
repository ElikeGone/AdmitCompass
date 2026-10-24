"""Code orchestrator (not an AI agent).

Fixed, bounded sequence:
  Pathway Matcher -> Evidence Analyst -> Strategy Planner -> Skeptic -> [<=1 revision of one agent + downstream]
Every handoff, tool call, model call, validation, and grounding decision is appended to the trace.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from .agents import prompts
from .agents.grounding import (
    ground_evidence, ground_pathway, ground_skeptic, ground_strategy, is_blocking,
)
from .agents.runner import AgentFailure, AgentResult, run_agent
from .core.budget import BudgetExceeded, RunBudget
from .core.config import redact_secrets
from .core.llm import ChatFn
from .core.usage import UsageRecord
from .schemas.agents import (
    AgentUsage, EvidenceOutput, GroundingViolation, PathwayOutput, ProgramFactView, ProgramRecommendation,
    RecommendationReport, SkepticOutput, StrategyOutput, TraceEvent,
)
from .schemas.applicant import ApplicantProfile
from .tools.agent_tools import ToolBox, compare_metrics
from .tools.evidence_store import EvidenceStore

MAX_REVISIONS = 1
REPORT_FACTS = ("location", "test_policy", "tuition", "cost_of_attendance", "stem_designation", "employment_rate",
                "median_base_salary", "international_employment", "sponsorship")
DISCLAIMERS = [
    "Decision support only — not admissions, legal, or immigration advice.",
    "No admission probabilities are estimated. Sponsorship is never inferred from employer lists.",
    "STEM designation does not by itself guarantee any immigration benefit; confirm with the school's DSO and a qualified attorney.",
    "Confirm deadlines, costs, and requirements on official school pages before acting.",
]
AGENT_SPECS = {
    "pathway_matcher": (prompts.PATHWAY, PathwayOutput, ("search_programs", "get_program_overview")),
    "evidence_analyst": (prompts.EVIDENCE, EvidenceOutput, ("get_program_facts", "get_evidence", "compare_employment_metrics", "get_sponsorship_evidence")),
    "strategy_planner": (prompts.STRATEGY, StrategyOutput, ("get_program_facts",)),
    "skeptic": (prompts.SKEPTIC, SkepticOutput, ("get_evidence", "get_program_facts", "compare_employment_metrics", "get_sponsorship_evidence")),
}
ORDER = ["pathway_matcher", "evidence_analyst", "strategy_planner"]


errlog = logging.getLogger("admitcompass.errors")  # raw error detail stays server-side

class Orchestrator:
    def __init__(self, chat: ChatFn, store: EvidenceStore, budget: RunBudget | None = None, model: str = "gpt-6-luna",
                 optimized: bool = True):
        self.chat, self.store, self.model = chat, store, model
        # optimized=True (default since Step 7): repair-mode grounding retry + downgrade evidence-less "verified" claims.
        # optimized=False reproduces the Step 5 behaviour (full re-run of the tool loop; schema retry).
        self.optimized = optimized
        self.budget = budget or RunBudget()
        self.trace: list[TraceEvent] = []
        self.usages: dict[str, list[UsageRecord]] = {}
        self.violations: list[GroundingViolation] = []
        self.toolbox = ToolBox(store, self.budget, lambda agent, tool, d: self.event("tool_call", agent, {"tool": tool, **d}))
        self.outputs: dict[str, Any] = {}

    def event(self, kind: str, agent: str, detail: dict | None = None) -> None:
        self.trace.append(TraceEvent(seq=len(self.trace) + 1, kind=kind, agent=agent, detail=detail or {}))

    # ----- one agent step: run -> ground -> (one grounding retry) -> sanitized output -----
    def _payload(self, agent: str, profile: ApplicantProfile) -> dict:
        prof = profile.known_fields()
        if agent == "pathway_matcher":
            return {"applicant_profile": prof}
        if agent == "evidence_analyst":
            return {"applicant_profile": prof, "pathway": self.outputs["pathway_matcher"].model_dump(mode="json")}
        if agent == "strategy_planner":
            return {"applicant_profile": prof,
                    "shortlist": [c.model_dump() for c in self.outputs["pathway_matcher"].candidates],
                    "evidence": self.outputs["evidence_analyst"].model_dump(mode="json")}
        return {"applicant_profile": prof,
                **{k: v.model_dump(mode="json") for k, v in self.outputs.items()},
                "deterministic_grounding_violations": [v.model_dump() for v in self.violations],
                "deterministic_metric_comparability": self._comparability()}

    def _ground(self, agent: str, out: Any, profile: ApplicantProfile, revisions_left: int):
        if agent == "pathway_matcher":
            return ground_pathway(self.store, out)
        if agent == "evidence_analyst":
            ids = [c.program_id for c in self.outputs["pathway_matcher"].candidates]
            return ground_evidence(self.store, profile, out, ids)
        if agent == "strategy_planner":
            return ground_strategy(self.store, out)
        return ground_skeptic(out, revisions_left)

    def _step(self, agent: str, profile: ApplicantProfile, feedback: str | None = None, revisions_left: int = 0):
        system, schema, tools = AGENT_SPECS[agent]
        self.event("agent_start", agent, {"revision_feedback": bool(feedback)})
        result: AgentResult = run_agent(agent=agent, system=system, user_payload=self._payload(agent, profile),
                                        schema=schema, tool_names=tools, chat=self.chat, toolbox=self.toolbox,
                                        budget=self.budget, event=self.event, extra_feedback=feedback,
                                        downgrade_unsupported_verified=self.optimized)
        self.usages.setdefault(agent, []).extend(result.usages)
        out, v = self._ground(agent, result.output, profile, revisions_left)
        self.event("grounding", agent, {"violations": len(v), "rules": sorted({x.rule for x in v}),
                                        "details": [x.model_dump() for x in v]})
        if is_blocking(v):
            fb = ("Your previous answer had grounding errors; fix them and answer again:\n"
                  + "\n".join(f"- {x.rule}: {x.detail}" for x in v))
            self.event("grounding", agent, {"retry": True, "mode": "repair" if self.optimized else "full"})
            if self.optimized:
                # Repair mode: one request, no tools. The agent gets its previous answer, the exact errors, and the
                # evidence it already retrieved; grounding runs again on the result, so nothing is weakened.
                payload = {**self._payload(agent, profile),
                           "repair": {"previous_answer": result.output.model_dump(mode="json"),
                                      "grounding_errors": [x.model_dump() for x in v],
                                      "evidence_already_retrieved": self.toolbox.by_agent.get(agent, [])}}
                result = run_agent(agent=agent, system=system, user_payload=payload, schema=schema, tool_names=(),
                                   chat=self.chat, toolbox=self.toolbox, budget=self.budget, event=self.event,
                                   extra_feedback=(feedback + "\n" if feedback else "") + fb +
                                   "\nREPAIR MODE: no tools. Fix only the listed errors using evidence_already_retrieved; "
                                   "drop any claim you cannot support. Keep everything else unchanged.",
                                   downgrade_unsupported_verified=True)
            else:
                result = run_agent(agent=agent, system=system, user_payload=self._payload(agent, profile), schema=schema,
                                   tool_names=tools, chat=self.chat, toolbox=self.toolbox, budget=self.budget,
                                   event=self.event, extra_feedback=(feedback + "\n" if feedback else "") + fb)
            self.usages[agent].extend(result.usages)
            out, v = self._ground(agent, result.output, profile, revisions_left)
            self.event("grounding", agent, {"violations_after_retry": len(v), "rules": sorted({x.rule for x in v}),
                                            "details": [x.model_dump() for x in v]})
        self.violations.extend(v)
        if agent == "pathway_matcher" and not out.candidates:
            raise AgentFailure("pathway_matcher produced no valid program candidates")
        if agent == "evidence_analyst" and not out.dossiers:
            raise AgentFailure("evidence_analyst produced no valid dossiers")
        self.outputs[agent] = out
        return out

    def _comparability(self) -> list[dict]:
        if "pathway_matcher" not in self.outputs:
            return []
        ids = [c.program_id for c in self.outputs["pathway_matcher"].candidates]
        return [compare_metrics(self.store, ids, m) for m in ("employment_rate", "median_base_salary")] if len(ids) > 1 else []

    # ----- main entry -----
    def run(self, profile: ApplicantProfile) -> RecommendationReport:
        run_id = uuid.uuid4().hex[:12]
        started = time.perf_counter()
        status, error, revision_target = "completed", None, None
        try:
            for i, agent in enumerate(ORDER):
                self._step(agent, profile)
                nxt = ORDER[i + 1] if i + 1 < len(ORDER) else "skeptic"
                self.event("handoff", agent, {"to": nxt, "output_type": type(self.outputs[agent]).__name__})
            skeptic = self._step("skeptic", profile, revisions_left=MAX_REVISIONS)
            if skeptic.revision_request:
                target = skeptic.revision_request.target_agent
                revision_target = target
                findings = [f.model_dump() for f in skeptic.findings if f.target_agent == target]
                fb = ("REVISION REQUESTED BY SKEPTIC (one revision allowed). Address these findings:\n"
                      f"{skeptic.revision_request.instructions}\nFindings: {findings}")
                self.event("revision", "orchestrator", {"target": target, "findings": len(findings)})
                for agent in ORDER[ORDER.index(target):]:
                    self._step(agent, profile, feedback=fb if agent == target else None)
                    self.event("handoff", agent, {"to": "report" if agent == ORDER[-1] else ORDER[ORDER.index(agent) + 1],
                                                  "phase": "revision"})
        except BudgetExceeded as e:
            status, error = "stopped_budget", str(e)
            self.event("budget_stop", "orchestrator", {"reason": str(e), **self.budget.snapshot()})
        except AgentFailure as e:
            status, error = "failed_closed", redact_secrets(str(e))
            self.event("agent_failure", "orchestrator", {"error": error[:300]})
            errlog.error("run %s failed closed: %s", run_id, error[:300])
        except Exception as e:  # unexpected API/network errors also fail closed
            status, error = "failed_closed", redact_secrets(f"{type(e).__name__}: {str(e)[:300]}")
            self.event("agent_failure", "orchestrator", {"error": error})
            errlog.error("run %s failed closed: %s", run_id, error)
        if status == "completed" and self.violations:
            status = "completed_with_violations"
        report = self._report(run_id, profile, status, error, revision_target, time.perf_counter() - started)
        self.event("run_end", "orchestrator", {"status": status, **self.budget.snapshot()})
        return report

    # ----- report assembly (facts copied from the store, never from model text) -----
    def _fact_views(self, pid: str) -> list[ProgramFactView]:
        views = []
        for name in REPORT_FACTS:
            f = self.store.get_fact(pid, name)
            views.append(ProgramFactView(
                fact=name, status=f.status, value=f.value, period=f.period, definition=f.definition,
                evidence_ids=[e["evidence_id"] for e in f.evidence],
                verification_level=f.evidence[0]["verification_level"] if f.evidence else None,
                freshness_warning=f.freshness.get("warning"), note=f.note[:300]))
        return views

    def _report(self, run_id, profile, status, error, revision_target, elapsed) -> RecommendationReport:
        pw: PathwayOutput | None = self.outputs.get("pathway_matcher")
        ev: EvidenceOutput | None = self.outputs.get("evidence_analyst")
        recs = []
        if pw and ev and status != "failed_closed":
            dossiers = {d.program_id: d for d in ev.dossiers}
            for c in pw.candidates:
                d = dossiers.get(c.program_id)
                if not d:
                    continue
                p = self.store.get_program(c.program_id)
                recs.append(ProgramRecommendation(
                    program_id=c.program_id, program_name=f"{p.school} {p.program_name}", career_fit=c.career_fit,
                    fit_rationale=c.fit_rationale, tradeoffs=c.tradeoffs, affordability=d.affordability,
                    affordability_basis=d.affordability_basis, stem_status=d.stem_status,
                    sponsorship_status=d.sponsorship_status, facts=self._fact_views(c.program_id),
                    analyst_claims=d.claims, flags=d.flags))
        usage = []
        for agent, us in self.usages.items():
            def tot(attr):
                vals = [getattr(u, attr) for u in us]
                return None if any(v is None for v in vals) else sum(vals)
            usage.append(AgentUsage(agent=agent, calls=len(us), input_tokens=tot("input_tokens"),
                                    cached_input_tokens=tot("cached_input_tokens"), output_tokens=tot("output_tokens"),
                                    reasoning_tokens=tot("reasoning_tokens"),
                                    elapsed_seconds=round(sum(u.elapsed_seconds for u in us), 3),
                                    estimated_cost_usd=tot("estimated_cost_usd")))

        def total(attr):
            vals = [getattr(u, attr) for u in usage]
            return None if not vals or any(v is None for v in vals) else sum(vals)
        totals = {"input_tokens": total("input_tokens"), "cached_input_tokens": total("cached_input_tokens"),
                  "output_tokens": total("output_tokens"), "reasoning_tokens_within_output": total("reasoning_tokens"),
                  "reasoning_effort": getattr(self.chat, "reasoning_effort", None),
                  "model_requests": self.budget.requests,
                  "tool_calls": self.budget.tool_calls, "model_seconds": round(sum(u.elapsed_seconds for u in usage), 3),
                  "wall_seconds": round(elapsed, 3), "estimated_cost_usd": total("estimated_cost_usd"),
                  "cost_basis": "unknown: no documented gpt-6-luna price configured" if total("estimated_cost_usd") is None else "documented price",
                  "budget": self.budget.snapshot()}
        return RecommendationReport(
            run_id=run_id, profile_id=profile.profile_id, status=status, model=self.model,
            target_roles=pw.target_roles if pw else [], recommendations=recs,
            excluded_programs=pw.excluded if pw else [], metric_comparability=self._comparability(),
            strategy=self.outputs.get("strategy_planner"), skeptic=self.outputs.get("skeptic"),
            revision_performed=revision_target is not None, revision_target=revision_target,
            grounding_violations=self.violations, usage_by_agent=usage, totals=totals,
            disclaimers=DISCLAIMERS, error=error)
