"""Baseline (Step 5 behaviour) vs optimized (Step 7) orchestrator on the SAME deterministic mock model.

The mock is built from the real saved run 20261023T180104Z:
  * tool-call rounds = the real tool calls each agent made (from trace.json, first pass);
  * final answers    = the real validated agent outputs (agent_outputs.json);
  * two failure types seen in real runs are re-injected identically in both modes:
      - Pathway Matcher's first answer has a 'verified_fact' claim with no evidence ids (schema failure);
      - Evidence Analyst's first answer has a verified claim with an unsupported number (grounding failure).
Prompt size is MEASURED as serialized request characters and ESTIMATED as tokens with tiktoken o200k_base.
These are not provider-reported tokens and not Portkey billing.

Usage: .venv\\Scripts\\python experiments\\tokenomics\\optimization_experiment.py
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import tiktoken  # noqa: E402  (experiment-only dependency; see requirements-experiments.txt)

from backend.app.agents.grounding import check_claim, profile_numbers  # noqa: E402
from backend.app.core.budget import RunBudget  # noqa: E402
from backend.app.core.llm import ChatResult  # noqa: E402
from backend.app.orchestrator import Orchestrator  # noqa: E402
from backend.app.schemas.applicant import ApplicantProfile  # noqa: E402
from backend.app.tools.evidence_store import EvidenceStore  # noqa: E402

RUN = ROOT / "experiments" / "agent_runs" / "20261023T180104Z_fixture-tech-pm-india"
OUT = Path(__file__).resolve().parent
ENC = tiktoken.get_encoding("o200k_base")


def tool_plans() -> dict[str, list[list[dict]]]:
    """Real first-pass tool-call rounds per agent, reconstructed from the saved trace."""
    plans: dict[str, list[list[dict]]] = {}
    seen_retry: set[str] = set()
    current = None
    for e in json.loads((RUN / "trace.json").read_text(encoding="utf-8")):
        a, d = e["agent"], e["detail"]
        if e["kind"] == "grounding" and d.get("retry"):
            seen_retry.add(a)
        if a in seen_retry:
            continue
        if e["kind"] == "llm_call" and d.get("tool_calls_requested"):
            current = []
            plans.setdefault(a, []).append(current)
        elif e["kind"] == "tool_call" and current is not None:
            args = d["args"] if isinstance(d["args"], dict) else json.loads(d["args"])
            current.append({"name": d["tool"], "args": args})
    return plans


class ReplayModel:
    """Deterministic, responsive mock: decides what to return from the conversation it is given."""

    def __init__(self):
        self.outputs = json.loads((RUN / "agent_outputs.json").read_text(encoding="utf-8"))
        self.plans = tool_plans()
        self.requests: list[dict] = []
        self.n = 0

    def _answer(self, agent: str, retry_kind: str | None) -> dict:
        out = copy.deepcopy(self.outputs[agent])
        if agent == "pathway_matcher" and retry_kind != "validation":
            out.setdefault("claims", []).append({"text": "MIT Sloan is STEM-designated.", "label": "verified_fact"})
        if agent == "evidence_analyst" and retry_kind != "grounding":
            out["dossiers"][0]["claims"].append({"text": "MIT Sloan tuition is $99,999 for 2026-2027.", "label": "verified_fact",
                                                 "evidence_ids": ["ev-mit-sloan-mba-tuition"]})
        return out

    def __call__(self, messages, tools, label, tool_choice="auto"):
        self.n += 1
        payload = json.dumps(messages, default=str) + json.dumps(tools or [], default=str)
        self.requests.append({"agent": label, "chars": len(payload), "est_tokens": len(ENC.encode(payload)),
                              "tools_offered": bool(tools) and tool_choice != "none"})
        text = " ".join(str(m.get("content", "")) for m in messages)
        retry = "grounding" if "grounding errors" in text else "validation" if "Your JSON was invalid" in text else None
        rounds_done = sum(1 for m in messages if m.get("tool_calls"))
        plan = self.plans.get(label, [])
        if tools and tool_choice != "none" and rounds_done < len(plan):
            calls = [{"id": f"c{self.n}-{i}", "name": c["name"], "arguments": json.dumps(c["args"])} for i, c in enumerate(plan[rounds_done])]
            return ChatResult(content=None, tool_calls=calls, usage=None,
                              assistant_message={"role": "assistant", "content": "", "tool_calls": [
                                  {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}} for c in calls]})
        return ChatResult(content=json.dumps(self._answer(label, retry)), usage=None)


def run_mode(optimized: bool) -> dict:
    profile = ApplicantProfile.model_validate_json((RUN / "input_profile.json").read_text(encoding="utf-8"))
    store = EvidenceStore.load()
    model = ReplayModel()
    orch = Orchestrator(model, store, budget=RunBudget(max_requests=40, max_total_tokens=10**9, max_tool_calls=80,
                                                      max_seconds=600), optimized=optimized)
    rep = orch.run(profile)
    per_agent: dict[str, dict] = {}
    for r in model.requests:
        a = per_agent.setdefault(r["agent"], {"requests": 0, "chars": 0, "est_tokens": 0})
        a["requests"] += 1
        a["chars"] += r["chars"]
        a["est_tokens"] += r["est_tokens"]
    claims = [(rec.program_id, c) for rec in rep.recommendations for c in rec.analyst_claims]
    regrounding = [p for pid, c in claims for p in check_claim(store, c, pid, profile_numbers(profile))]
    ev = [e for e in orch.trace if e.kind in ("validation", "grounding")]
    return {
        "mode": "optimized" if optimized else "baseline",
        "status": rep.status,
        "model_requests": len(model.requests),
        "serialized_request_chars": sum(r["chars"] for r in model.requests),
        "estimated_input_tokens_o200k": sum(r["est_tokens"] for r in model.requests),
        "tool_calls_executed": sum(1 for e in orch.trace if e.kind == "tool_call" and not e.detail.get("cached_repeat")),
        "tool_calls_served_from_run_cache": sum(1 for e in orch.trace if e.kind == "tool_call" and e.detail.get("cached_repeat")),
        "validation_failures": sum(1 for e in ev if e.kind == "validation" and not e.detail.get("ok")),
        "downgraded_verified_claims": sum(e.detail.get("downgraded_verified_claims", 0) for e in ev if e.kind == "validation"),
        "grounding_retries": sum(1 for e in ev if e.kind == "grounding" and e.detail.get("retry")),
        "per_agent": per_agent,
        "quality": {
            "recommended_programs": [r.program_id for r in rep.recommendations],
            "analyst_claims": len(claims),
            "verified_claims": sum(1 for _, c in claims if c.label.value == "verified_fact"),
            "verified_claim_evidence_ids": sorted({i for _, c in claims for i in c.evidence_ids}),
            "final_claims_failing_regrounding": len(regrounding),
            "grounding_violations_recorded": [v.rule for v in rep.grounding_violations],
            "strategy_weeks": len(rep.strategy.weekly_plan) if rep.strategy else 0,
            "skeptic_findings": len(rep.skeptic.findings) if rep.skeptic else 0,
            "pathway_claim_labels": [c.label.value for c in orch.outputs["pathway_matcher"].claims],
        },
    }


def main() -> int:
    base, opt = run_mode(False), run_mode(True)
    pct = lambda a, b: round(100 * (a - b) / a, 1) if a else None  # noqa: E731
    result = {
        "method": __doc__.strip().splitlines()[0],
        "measurement_note": ("serialized_request_chars is measured exactly; estimated_input_tokens_o200k is a tokenizer "
                             "ESTIMATE (gpt-6-luna's tokenizer is not published). Neither is provider-reported usage."),
        "baseline": base, "optimized": opt,
        "reduction": {
            "model_requests": base["model_requests"] - opt["model_requests"],
            "model_requests_pct": pct(base["model_requests"], opt["model_requests"]),
            "estimated_input_tokens": base["estimated_input_tokens_o200k"] - opt["estimated_input_tokens_o200k"],
            "estimated_input_tokens_pct": pct(base["estimated_input_tokens_o200k"], opt["estimated_input_tokens_o200k"]),
            "serialized_chars_pct": pct(base["serialized_request_chars"], opt["serialized_request_chars"]),
        },
        "quality_identical": {k: base["quality"][k] == opt["quality"][k] for k in base["quality"]},
    }
    (OUT / "optimization_comparison.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("reduction", "quality_identical")}, indent=2))
    for m in (base, opt):
        print(m["mode"], m["status"], m["model_requests"], m["estimated_input_tokens_o200k"], m["per_agent"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
