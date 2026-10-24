"""Agent/orchestrator tests with a scripted (mock) LLM — no network, no cost."""
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.agents.grounding import (
    check_claim, ground_evidence, ground_strategy, risky_language,
)
from backend.app.core.budget import RunBudget
from backend.app.core.llm import ChatResult
from backend.app.core.usage import record_from_usage
from backend.app.orchestrator import Orchestrator
from backend.app.schemas.agents import EvidenceOutput, StrategyOutput
from backend.app.schemas.applicant import ApplicantProfile
from backend.app.schemas.claims import Claim
from backend.app.tools.evidence_store import EvidenceStore

FIX = Path(__file__).resolve().parents[1] / "data" / "fixtures"


@pytest.fixture(scope="module")
def store():
    return EvidenceStore.load()


@pytest.fixture
def profile():
    return ApplicantProfile.model_validate_json((FIX / "applicant_tech_pm.json").read_text())


# ---------- scripted mock LLM ----------
PATHWAY = {
    "target_roles": [{"title": "Product Manager", "rationale": "Engineering lead moving to PM"}],
    "candidates": [
        {"program_id": "yale-som-mba", "career_fit": "moderate", "fit_rationale": "General management", "tradeoffs": ["Smaller tech pipeline"]},
        {"program_id": "chicago-booth-mba", "career_fit": "strong", "fit_rationale": "Tech placements", "tradeoffs": ["Cost"]},
    ],
    "excluded": [{"program_id": "rice-jones-mba", "reason": "Energy focus"}],
    "missing_profile_info": ["test score"],
    "claims": [{"text": "Booth is STEM-designated", "label": "verified_fact", "evidence_ids": ["ev-chicago-booth-mba-stem-designation"]}],
}


def dossier(pid, **kw):
    # a well-behaved analyst reports the store's sponsorship level (DOL employer evidence makes some programs non-unknown)
    from backend.app.agents.grounding import expected_sponsorship
    from backend.app.tools.evidence_store import default_store
    base = {"program_id": pid, "claims": [{"text": "Cost fits budget", "label": "inference"}],
            "affordability": "within_budget", "affordability_basis": "COA vs budget", "stem_status": "verified_designated",
            "sponsorship_status": expected_sponsorship(default_store(), pid), "source_strength": "official", "flags": []}
    base.update(kw)
    return base


EVIDENCE = {"dossiers": [
    dossier("yale-som-mba", claims=[{"text": "Yale reported 82.1% with offers by three months for the Class of 2025.",
                                     "label": "verified_fact", "evidence_ids": ["ev-yale-som-mba-employment-rate"]}]),
    dossier("chicago-booth-mba", claims=[{"text": "Booth's 2026-27 cost of attendance is $132,449.", "label": "verified_fact",
                                          "evidence_ids": ["ev-chicago-booth-mba-cost-of-attendance"]}]),
], "metric_comparisons": [{"program_ids": ["yale-som-mba", "chicago-booth-mba"], "metric": "employment_rate",
                           "treated_as_comparable": False, "reason": "different definitions"}],
    "unsupported_claims_flagged": []}

STRATEGY = {
    "test_guidance": {"recommendation": "either_gmat_or_gre", "rationale": "Both accepted",
                      "evidence_ids": ["ev-yale-som-mba-test-policy"]},
    "gaps": [{"gap": "No test score", "severity": "high", "action": "Take a diagnostic"}],
    "weekly_plan": [{"week": 1, "priority": "high", "actions": ["Take a GMAT and a GRE diagnostic"]}],
    "roadmap": [{"phase": "Prepare", "timing": "Weeks 1-6", "milestones": ["Test done"], "human_checkpoint": False},
                {"phase": "Decide", "timing": "After results", "milestones": ["Choose schools"], "human_checkpoint": True}],
    "claims": [],
}
SKEPTIC = {"findings": [{"target_agent": "evidence_analyst", "target_ref": "yale-som-mba", "category": "weak_source",
                         "severity": "medium", "issue": "Denominator undefined", "required_fix": "Say so"}],
           "revision_request": None, "overall_assessment": "Reasonable"}


def usage():
    return record_from_usage("gpt-6-luna", {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150,
                                            "prompt_tokens_details": {"cached_tokens": 20}}, 0.01)


def reply(obj):
    return ChatResult(content=json.dumps(obj) if not isinstance(obj, str) else obj, usage=usage())


def tool(name, args):
    return ChatResult(content=None, usage=usage(), tool_calls=[{"id": f"c-{name}", "name": name, "arguments": json.dumps(args)}],
                      assistant_message={"role": "assistant", "content": ""})


class ScriptedChat:
    def __init__(self, script):
        self.script = {k: list(v) for k, v in script.items()}
        self.calls = []

    def __call__(self, messages, tools, label, tool_choice="auto"):
        self.calls.append((label, tool_choice))
        if not self.script.get(label):
            raise RuntimeError(f"no scripted reply for {label}")
        r = self.script[label].pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def happy_script(**over):
    s = {"pathway_matcher": [tool("search_programs", {"max_cost_of_attendance": 135000}), reply(PATHWAY)],
         "evidence_analyst": [tool("get_program_facts", {"program_id": "yale-som-mba", "fields": ["employment_rate"]}),
                              reply(EVIDENCE)],
         "strategy_planner": [reply(STRATEGY)],
         "skeptic": [reply(SKEPTIC)]}
    s.update(over)
    return s


def run(store, profile, script, budget=None):
    chat = ScriptedChat(script)
    orch = Orchestrator(chat, store, budget=budget)
    return orch, orch.run(profile), chat


# ---------- schemas ----------
def test_fixtures_valid_and_fictional():
    for f in FIX.glob("applicant_*.json"):
        p = ApplicantProfile.model_validate_json(f.read_text())
        assert p.is_fictional


def test_profile_rejects_sensitive_extra_fields():
    with pytest.raises(ValidationError):
        ApplicantProfile(profile_id="x", is_fictional=True, passport_number="123")


def test_profile_allows_unknowns():
    p = ApplicantProfile(profile_id="x", is_fictional=True)
    assert p.max_total_budget_usd_per_year is None and p.test_status.value == "unknown"


# ---------- happy path / handoffs / tools ----------
def test_full_run_handoffs_and_tool_trace(store, profile):
    orch, rep, chat = run(store, profile, happy_script())
    assert rep.status == "completed", rep.grounding_violations
    assert [r.program_id for r in rep.recommendations] == ["yale-som-mba", "chicago-booth-mba"]
    handoffs = [(e.agent, e.detail["to"]) for e in orch.trace if e.kind == "handoff"]
    assert handoffs == [("pathway_matcher", "evidence_analyst"), ("evidence_analyst", "strategy_planner"),
                        ("strategy_planner", "skeptic")]
    tools = [(e.agent, e.detail["tool"]) for e in orch.trace if e.kind == "tool_call"]
    assert tools == [("pathway_matcher", "search_programs"), ("evidence_analyst", "get_program_facts")]
    assert rep.totals["input_tokens"] == 600 and rep.totals["cached_input_tokens"] == 120
    assert rep.totals["estimated_cost_usd"] is None


def test_report_facts_come_from_store_not_model(store, profile):
    _, rep, _ = run(store, profile, happy_script())
    booth = next(r for r in rep.recommendations if r.program_id == "chicago-booth-mba")
    coa = next(f for f in booth.facts if f.fact == "cost_of_attendance")
    assert coa.value == 132449 and coa.period == "2026-2027" and coa.evidence_ids == ["ev-chicago-booth-mba-cost-of-attendance"]
    assert coa.verification_level == "rechecked_first_hand"
    assert next(f for f in booth.facts if f.fact == "sponsorship").status == "unknown"


# ---------- grounding ----------
def test_unknown_program_dropped_then_fail_closed(store, profile):
    bad = {**PATHWAY, "candidates": [{"program_id": "made-up-school-mba", "career_fit": "strong", "fit_rationale": "x"}]}
    _, rep, _ = run(store, profile, happy_script(pathway_matcher=[reply(bad), reply(bad)]))
    assert rep.status == "failed_closed" and not rep.recommendations
    assert any(v.rule == "unknown_program_id" for v in rep.grounding_violations) or "no valid program" in rep.error


def test_unsupported_number_in_verified_claim_dropped(store, profile):
    ev = json.loads(json.dumps(EVIDENCE))
    ev["dossiers"][0]["claims"].append({"text": "Yale placed 97% of graduates.", "label": "verified_fact",
                                        "evidence_ids": ["ev-yale-som-mba-employment-rate"]})
    _, rep, _ = run(store, profile, happy_script(evidence_analyst=[reply(ev), reply(ev)]))
    assert any(v.rule == "unsupported_claim" and "97" in v.detail for v in rep.grounding_violations)
    yale = next(r for r in rep.recommendations if r.program_id == "yale-som-mba")
    assert all("97%" not in c.text for c in yale.analyst_claims)


def test_missing_evidence_id_rejected(store):
    probs = check_claim(store, Claim(text="x", label="verified_fact", evidence_ids=["ev-fake"]))
    assert probs and "does not exist" in probs[0]


def test_evidence_from_wrong_program_rejected(store):
    c = Claim(text="Cost is $132,449", label="verified_fact", evidence_ids=["ev-chicago-booth-mba-cost-of-attendance"])
    assert check_claim(store, c, "yale-som-mba")


def test_sponsorship_and_affordability_corrected_to_store(store, profile):
    ev = EvidenceOutput.model_validate({**EVIDENCE, "dossiers": [
        dossier("yale-som-mba", sponsorship_status="unknown", affordability="over_budget"),
        dossier("mit-sloan-mba", sponsorship_status="employer_specific_evidence")]})
    out, v = ground_evidence(store, profile, ev, ["yale-som-mba", "mit-sloan-mba"])
    # Yale: its official report lists employers with DOL H-1B filings -> employer-specific (historical) evidence
    assert out.dossiers[0].sponsorship_status == "employer_specific_evidence"
    assert out.dossiers[0].affordability == "within_budget"  # 128,976 <= 135,000 (verified COA)
    # MIT: no employer list in the official report -> the model's claim is corrected to unknown
    assert out.dossiers[1].sponsorship_status == "unknown"
    assert {"sponsorship_status_mismatch", "affordability_mismatch"} <= {x.rule for x in v}


def test_unknown_cost_means_unknown_affordability(store, profile):
    ev = EvidenceOutput.model_validate({"dossiers": [dossier("mit-sloan-mba", affordability="within_budget")]})
    out, _ = ground_evidence(store, profile, ev, ["mit-sloan-mba"])
    assert out.dossiers[0].affordability == "unknown"  # MIT cost of attendance not verified


def test_mismatched_employment_definitions_not_comparable(store, profile):
    ev = EvidenceOutput.model_validate({"dossiers": [dossier("yale-som-mba"), dossier("chicago-booth-mba")],
                                        "metric_comparisons": [{"program_ids": ["yale-som-mba", "chicago-booth-mba"],
                                                                "metric": "employment_rate", "treated_as_comparable": True,
                                                                "reason": "both ~3 months"}]})
    out, v = ground_evidence(store, profile, ev, ["yale-som-mba", "chicago-booth-mba"])
    assert out.metric_comparisons[0].treated_as_comparable is False
    assert any(x.rule == "incomparable_metrics" for x in v)


def test_risky_language_detection():
    assert risky_language("This guarantees admission") == ["guarantee"]
    assert risky_language("Admission is not guaranteed") == []
    assert "admission_odds" in risky_language("You have a 70% chance of getting in")
    assert "visa_eligibility_assertion" in risky_language("You will be eligible for STEM OPT")
    assert risky_language("Confirm STEM OPT eligibility with the DSO") == []


def test_invented_dates_dropped_from_plan(store):
    s = StrategyOutput.model_validate({**STRATEGY, "weekly_plan": [
        {"week": 1, "priority": "high", "actions": ["Submit Round 1 by September 10", "Draft resume"]}]})
    out, v = ground_strategy(store, s)
    assert out.weekly_plan[0].actions == ["Draft resume"]
    assert any(x.rule == "risky_or_dated_action" for x in v)


# ---------- revision limit ----------
def test_one_revision_then_stop(store, profile):
    sk = {**SKEPTIC, "revision_request": {"target_agent": "strategy_planner", "instructions": "Add budget checkpoint"}}
    orch, rep, chat = run(store, profile, happy_script(skeptic=[reply(sk)], strategy_planner=[reply(STRATEGY), reply(STRATEGY)]))
    assert rep.revision_performed and rep.revision_target == "strategy_planner"
    assert [c[0] for c in chat.calls].count("skeptic") == 1           # skeptic not re-run
    assert [c[0] for c in chat.calls].count("strategy_planner") == 2  # original + one revision
    assert sum(1 for e in orch.trace if e.kind == "revision") == 1


def test_revision_of_pathway_reruns_downstream(store, profile):
    sk = {**SKEPTIC, "revision_request": {"target_agent": "pathway_matcher", "instructions": "Reconsider"}}
    _, rep, chat = run(store, profile, happy_script(
        skeptic=[reply(sk)], pathway_matcher=[reply(PATHWAY), reply(PATHWAY)],
        evidence_analyst=[reply(EVIDENCE), reply(EVIDENCE)], strategy_planner=[reply(STRATEGY), reply(STRATEGY)]))
    assert rep.status == "completed"
    assert [c[0] for c in chat.calls] == ["pathway_matcher", "evidence_analyst", "strategy_planner", "skeptic",
                                         "pathway_matcher", "evidence_analyst", "strategy_planner"]


# ---------- budget ----------
def test_budget_stops_further_calls(store, profile):
    orch, rep, chat = run(store, profile, happy_script(), budget=RunBudget(max_requests=3, max_total_tokens=10**6, max_tool_calls=10))
    assert rep.status == "stopped_budget" and len(chat.calls) == 3
    assert any(e.kind == "budget_stop" for e in orch.trace)
    assert "request limit" in rep.error


def test_token_budget(store, profile):
    _, rep, chat = run(store, profile, happy_script(), budget=RunBudget(max_requests=50, max_total_tokens=300, max_tool_calls=10))
    assert rep.status == "stopped_budget" and len(chat.calls) == 2


def test_tool_loop_bounded(store, profile):
    loop = [tool("search_programs", {}) for _ in range(4)] + [reply(PATHWAY)]
    _, rep, chat = run(store, profile, happy_script(pathway_matcher=loop))
    assert rep.status == "completed"
    assert chat.calls[4] == ("pathway_matcher", "none")  # 5th turn: tools disabled


# ---------- failures ----------
def test_invalid_json_retry_then_success(store, profile):
    _, rep, _ = run(store, profile, happy_script(strategy_planner=[reply("not json"), reply(STRATEGY)]))
    assert rep.status == "completed"


def test_invalid_json_twice_fails_closed(store, profile):
    _, rep, _ = run(store, profile, happy_script(strategy_planner=[reply("{}"), reply("not json")]))
    assert rep.status == "failed_closed" and not rep.recommendations and "strategy_planner" in rep.error


def test_api_error_fails_closed(store, profile):
    _, rep, _ = run(store, profile, happy_script(evidence_analyst=[RuntimeError("503 upstream")]))
    assert rep.status == "failed_closed" and "503" in rep.error


# ---------- reproducibility ----------
def test_deterministic_layer_reproducible(store, profile):
    _, a, _ = run(store, profile, happy_script())
    _, b, _ = run(store, profile, happy_script())
    strip = lambda r: r.model_dump(exclude={"run_id", "totals", "usage_by_agent"})
    assert strip(a) == strip(b)


def test_short_academic_year_not_treated_as_number():
    from backend.app.agents.grounding import numbers_in
    assert numbers_in("2026-27 cost is $132,449") == {2026.0, 2027.0, 132449.0}
    assert numbers_in("median $175K") == {175000.0}


# ---------- Responses API adapter (pure conversion; no network) ----------
def test_responses_input_conversion():
    from backend.app.core.llm import _to_responses_input, _to_responses_tools
    msgs = [{"role": "system", "content": "S"}, {"role": "user", "content": "U"},
            {"_responses_items": [{"type": "reasoning", "id": "r1", "encrypted_content": "x"},
                                  {"type": "function_call", "call_id": "c1", "name": "t", "arguments": "{}"}]},
            {"role": "tool", "tool_call_id": "c1", "content": "{\"ok\":1}"}]
    instr, items = _to_responses_input(msgs)
    assert instr == "S"
    assert [i.get("type", i.get("role")) for i in items] == ["user", "user", "reasoning", "function_call", "function_call_output"]
    assert "json" in items[0]["content"].lower()  # JSON-mode requirement
    assert items[-1] == {"type": "function_call_output", "call_id": "c1", "output": "{\"ok\":1}"}
    spec = _to_responses_tools([{"type": "function", "function": {"name": "t", "description": "d", "parameters": {}}}])
    assert spec == [{"type": "function", "name": "t", "description": "d", "parameters": {}}]


def test_usage_parses_responses_shape_with_reasoning():
    u = record_from_usage("gpt-6-luna", {"input_tokens": 300, "output_tokens": 120, "total_tokens": 420,
                                          "input_tokens_details": {"cached_tokens": 64},
                                          "output_tokens_details": {"reasoning_tokens": 80}}, 1.0)
    assert (u.input_tokens, u.cached_input_tokens, u.output_tokens, u.reasoning_tokens, u.total_tokens) == (300, 64, 120, 80, 420)


def test_budget_counts_tokens_across_tool_rounds(store, profile):
    orch, rep, chat = run(store, profile, happy_script())
    # 6 model requests x 150 tokens each (2 tool rounds + 4 final answers)
    assert orch.budget.requests == 6 and orch.budget.total_tokens == 900


# ---------- regressions from the first real run (2026-10-23) ----------
def test_profile_budget_number_allowed_in_verified_claim(store, profile):
    ev = EvidenceOutput.model_validate({"dossiers": [dossier("chicago-booth-mba", claims=[
        {"text": "Cost of attendance is $132,449 for 2026-2027, within the stated budget of $135,000.",
         "label": "verified_fact", "evidence_ids": ["ev-chicago-booth-mba-cost-of-attendance"]}])]})
    out, v = ground_evidence(store, profile, ev, ["chicago-booth-mba"])
    assert not v and len(out.dossiers[0].claims) == 1


def test_number_not_in_evidence_or_profile_still_rejected(store, profile):
    c = Claim(text="Cost is $150,000", label="verified_fact", evidence_ids=["ev-chicago-booth-mba-cost-of-attendance"])
    from backend.app.agents.grounding import profile_numbers
    assert check_claim(store, c, "chicago-booth-mba", profile_numbers(profile))


def test_repeated_identical_tool_call_served_from_cache(store, profile):
    args = {"program_ids": ["yale-som-mba", "chicago-booth-mba"], "metric": "employment_rate"}
    script = happy_script(evidence_analyst=[tool("compare_employment_metrics", args),
                                            tool("compare_employment_metrics", args), reply(EVIDENCE)])
    orch, rep, _ = run(store, profile, script)
    calls = [e.detail for e in orch.trace if e.kind == "tool_call" and e.detail["tool"] == "compare_employment_metrics"]
    assert len(calls) == 2 and calls[1].get("cached_repeat") is True


def test_first_pass_grounding_details_logged(store, profile):
    ev = json.loads(json.dumps(EVIDENCE))
    ev["dossiers"][0]["claims"].append({"text": "Yale placed 97% of graduates.", "label": "verified_fact",
                                        "evidence_ids": ["ev-yale-som-mba-employment-rate"]})
    orch, _, _ = run(store, profile, happy_script(evidence_analyst=[reply(ev), reply(EVIDENCE)]))
    first = next(e for e in orch.trace if e.kind == "grounding" and e.agent == "evidence_analyst")
    assert first.detail["violations"] == 1 and "97" in first.detail["details"][0]["detail"]


def test_hedged_sponsorship_statement_allowed_but_assertion_rejected(store):
    hedged = Claim(text="For the Class of 2025, 7.2% of full-time employment was outside the US. Employer-specific sponsorship evidence is unknown.",
                   label="verified_fact", evidence_ids=["ev-yale-som-mba-international-employment"])
    assertive = Claim(text="Most employers of Yale graduates sponsor H-1B visas.", label="verified_fact",
                      evidence_ids=["ev-yale-som-mba-international-employment"])
    assert check_claim(store, hedged, "yale-som-mba") == []
    assert check_claim(store, assertive, "yale-som-mba")


# ---------- Step 7 optimizations ----------
def test_repair_mode_retry_uses_one_request_without_tools(store, profile):
    ev = json.loads(json.dumps(EVIDENCE))
    ev["dossiers"][0]["claims"].append({"text": "Yale placed 97% of graduates.", "label": "verified_fact",
                                        "evidence_ids": ["ev-yale-som-mba-employment-rate"]})
    script = happy_script(evidence_analyst=[tool("get_program_facts", {"program_id": "yale-som-mba"}), reply(ev), reply(EVIDENCE)])
    orch, rep, chat = run(store, profile, script)
    ea = [c for c in chat.calls if c[0] == "evidence_analyst"]
    assert len(ea) == 3 and ea[-1] == ("evidence_analyst", "none")  # repair call: tools disabled
    assert any(e.kind == "grounding" and e.detail.get("mode") == "repair" for e in orch.trace)
    assert rep.status == "completed"


def test_baseline_mode_still_available(store, profile):
    ev = json.loads(json.dumps(EVIDENCE))
    ev["dossiers"][0]["claims"].append({"text": "Yale placed 97% of graduates.", "label": "verified_fact",
                                        "evidence_ids": ["ev-yale-som-mba-employment-rate"]})
    chat = ScriptedChat(happy_script(evidence_analyst=[reply(ev), reply(EVIDENCE)]))
    orch = Orchestrator(chat, store, optimized=False)
    orch.run(profile)
    assert any(e.kind == "grounding" and e.detail.get("mode") == "full" for e in orch.trace)


def test_evidence_less_verified_claim_downgraded_not_retried(store, profile):
    pw = {**PATHWAY, "claims": [{"text": "Booth is a strong fit", "label": "verified_fact"}]}
    orch, rep, chat = run(store, profile, happy_script(pathway_matcher=[reply(pw)]))
    assert rep.status == "completed" and [c[0] for c in chat.calls].count("pathway_matcher") == 1
    assert orch.outputs["pathway_matcher"].claims[0].label.value == "inference"
