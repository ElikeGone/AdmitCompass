"""Career Intelligence dashboard: deterministic views over a saved or live analysis. No model calls.

Every value returned here comes from (a) the saved/live RecommendationReport (what the agents produced, already
grounded) or (b) the evidence store. Calculations (budget gaps, task grouping) are plain arithmetic so they can
be tested exactly.
"""
from __future__ import annotations

import re
from typing import Any

from ..schemas.applicant import ApplicantProfile
from ..schemas.programs import parse_academic_year
from .catalog import stem_is_partial
from .evidence_store import EvidenceNotFoundError, EvidenceStore

TIMING = re.compile(r"weeks?\s*(\d+)\s*[-–]\s*(\d+)", re.I)


def _fact(rec: dict, name: str) -> dict | None:
    return next((f for f in rec.get("facts", []) if f["fact"] == name), None)


def _verified(f: dict | None) -> bool:
    return bool(f) and f.get("status") == "verified"


# ---------------- affordability ----------------
def affordability(profile: ApplicantProfile, rec: dict) -> dict:
    """Compare the applicant's budget with the published cost, only when the two measures are compatible.

    Compatible = applicant budget per academic year AND a verified one-year cost of attendance for an academic year.
    Tuition alone is shown as context but never compared with a total budget (it omits living costs).
    """
    coa, tuition = _fact(rec, "cost_of_attendance"), _fact(rec, "tuition")
    budget, period = profile.budget_usd, profile.budget_period
    out: dict[str, Any] = {
        "budget": budget, "budget_period": period,
        "cost_of_attendance": ({"value": coa["value"], "period": coa["period"], "evidence_ids": coa["evidence_ids"]}
                               if _verified(coa) else None),
        "tuition": ({"value": tuition["value"], "period": tuition["period"], "evidence_ids": tuition["evidence_ids"]}
                    if _verified(tuition) else None),
        "comparable": False, "gap": None, "status": None, "reason": "",
    }
    if budget is None:
        out.update(status="no_budget", reason="No budget was provided, so there's nothing to compare.")
    elif period != "per_academic_year":
        out.update(status="not_comparable",
                   reason="Your budget covers the whole program, but schools publish cost of attendance per academic year. "
                          "Comparing them would need assumptions about year two, so we don't.")
    elif not _verified(coa) or parse_academic_year(coa.get("period")) is None:
        out.update(status="no_cost",
                   reason="The school doesn't publish a one-year cost of attendance on the pages we checked. Tuition alone leaves out "
                          "living costs, so it isn't compared with your total budget.")
        # A third-party ESTIMATE can give context, clearly labeled; it never becomes the official comparison.
        from .supplementary import cost_summary
        est = cost_summary(rec["program_id"])["estimate_annual"]
        if est and parse_academic_year(est["period"]) is not None:
            out["estimate"] = {**est, "gap_estimate": round(budget - est["value"], 2)}
    else:
        gap = round(budget - coa["value"], 2)
        out.update(comparable=True, gap=gap, status="within" if gap >= 0 else "shortfall",
                   reason=("Published one-year cost of attendance is within your per-year budget." if gap > 0 else
                           "Published one-year cost of attendance equals your per-year budget — no headroom." if gap == 0 else
                           "Published one-year cost of attendance exceeds your per-year budget."))
    return out


# ---------------- international feasibility ----------------
def feasibility(rec: dict, profile: ApplicantProfile | None = None) -> dict:
    stem, intl, spon = _fact(rec, "stem_designation"), _fact(rec, "international_employment"), _fact(rec, "sponsorship")
    if _verified(stem):
        v = stem["value"]
        stem_out = {"status": "verified", "designated": v["designated"], "scope": v["scope"],
                    "partial": stem_is_partial(v["scope"]), "evidence_ids": stem["evidence_ids"]}
    else:
        stem_out = {"status": "unknown", "designated": None, "scope": None, "partial": False, "evidence_ids": []}
    return {
        "stem": stem_out,
        # A sourced statement is only an outcome *figure* if it states a statistic (% or $); e.g. Booth's source says
        # no international-specific statistics exist, which is a verified statement, not an outcome.
        "international_outcomes": ({"value": intl["value"], "period": intl.get("period"), "evidence_ids": intl["evidence_ids"],
                                    "kind": "figure" if re.search(r"[%$]", str(intl["value"])) else "statement"}
                                   if _verified(intl) else None),
        "sponsorship": ({"status": "employer_specific", "value": spon["value"], "evidence_ids": spon["evidence_ids"]}
                        if _verified(spon) else {"status": "unknown"}),
        "h1b_history": _h1b(rec["program_id"], profile),
        "notes": [
            "STEM designation is a program classification, not evidence that any employer will sponsor a visa.",
            "Eligibility for any immigration benefit depends on your own circumstances and current rules — confirm with the "
            "school's international office (DSO) or a qualified immigration attorney.",
        ],
    }


def _h1b(pid: str, profile: ApplicantProfile | None) -> dict:
    """Historical employer H-1B filings, scoped to the applicant's target occupation and city when they map to the dataset."""
    from .sponsorship import get_sponsorship_evidence, metro_for, occupation_for
    occ = occupation_for(" ".join(filter(None, [profile.target_function, *(profile.target_roles or [])]))) if profile else None
    city = metro_for(profile.long_term_location) if profile and profile.long_term_location else None
    return get_sponsorship_evidence(pid, occ, city)


# ---------------- program fit ----------------
def program_fit(rec: dict) -> dict:
    claims = rec.get("analyst_claims", [])
    supported = [c for c in claims if c["label"] == "verified_fact" and c.get("evidence_ids")]
    reasoning = [c for c in claims if c["label"] in ("inference", "advice")]
    unknown_claims = [c for c in claims if c["label"] == "unknown"]
    unknown_facts = [f["fact"] for f in rec.get("facts", []) if f.get("status") != "verified"]
    rationale = re.sub(r"^(verified_fact|inference|advice|unknown)\s*:\s*", "", rec.get("fit_rationale", ""), flags=re.I)
    return {"career_fit": rec.get("career_fit"), "why": rationale, "supported": supported, "reasoning": reasoning,
            "unknown_claims": unknown_claims, "unknown_facts": unknown_facts, "tradeoffs": rec.get("tradeoffs", [])}


# ---------------- pathway ----------------
def pathway(profile: ApplicantProfile, report: dict) -> dict:
    """Profile facts are things the applicant told us; gaps are AI-inferred by the Strategy Planner."""
    facts = []
    for e in profile.education:
        facts.append({"label": "Education", "value": f"{e.degree_level} in {e.field}" + (f" ({e.gpa_band})" if e.gpa_band else "")})
    if profile.years_work_experience is not None:
        facts.append({"label": "Experience", "value": f"{profile.years_work_experience:g} years"})
    if profile.current_function:
        facts.append({"label": "Current role", "value": profile.current_function + (f", {profile.current_industry}" if profile.current_industry else "")})
    if profile.quantitative_background:
        facts.append({"label": "Quantitative background", "value": profile.quantitative_background})
    if profile.test_status:
        facts.append({"label": "Tests", "value": profile.test_status.value.replace("_", " ")})
    strat = report.get("strategy") or {}
    gaps = [{"gap": g["gap"], "severity": g["severity"], "action": g["action"], "source": "Strategy Planner (AI-inferred)"}
            for g in sorted(strat.get("gaps", []), key=lambda g: ["high", "medium", "low"].index(g["severity"]))]
    return {
        "background": {"role": profile.current_function, "industry": profile.current_industry,
                       "years": profile.years_work_experience, "citizenship": profile.citizenship_country},
        "target": {"roles": [t["title"] for t in report.get("target_roles", [])], "function": profile.target_function,
                   "industry": profile.target_industry},
        "profile_facts": facts, "gaps": gaps,
    }


# ---------------- application workspace ----------------
def workspace(report: dict) -> dict:
    """Group weekly actions into the roadmap's phases by their 'Weeks a-b' timing; stable task ids for local progress."""
    strat = report.get("strategy") or {}
    weeks = strat.get("weekly_plan", [])
    tasks = [{"id": f"w{w['week']}-{i}", "week": w["week"], "priority": w["priority"], "text": a}
             for w in weeks for i, a in enumerate(w["actions"])]
    phases, used = [], set()
    for ph in strat.get("roadmap", []):
        m = TIMING.search(ph["timing"])
        ids = [t["id"] for t in tasks if m and int(m.group(1)) <= t["week"] <= int(m.group(2))]
        used.update(ids)
        phases.append({"phase": ph["phase"], "timing": ph["timing"], "milestones": ph["milestones"],
                       "human_checkpoint": ph["human_checkpoint"], "task_ids": ids})
    leftover = [t["id"] for t in tasks if t["id"] not in used]
    if leftover:
        phases.append({"phase": "Other planned actions", "timing": "", "milestones": [], "human_checkpoint": False, "task_ids": leftover})
    return {"tasks": tasks, "phases": phases, "test_guidance": strat.get("test_guidance"),
            "storage_note": "Progress is stored only in this browser (task ids and done flags — no personal details)."}


def deadlines(store: EvidenceStore, program_id: str) -> dict:
    try:
        prog = store.get_program(program_id)
    except EvidenceNotFoundError:
        return {"status": "not_in_store"}
    f = store.get_fact(program_id, "application_deadlines")
    if f.status == "verified":
        return {"status": "verified", "rounds": f.value, "cycle": f.period, "evidence": f.evidence}
    from .supplementary import verified as supp_verified
    s = next((x for x in supp_verified(program_id) if x.field == "application_deadlines" and x.source_type == "official"), None)
    if s:
        return {"status": "verified", "rounds": [{"round": r["round"], "deadline": r["deadline"]} for r in s.value], "cycle": s.period,
                "source_url": s.source_url, "notes": s.notes}
    return {"status": "not_checked" if not prog.facts["application_deadlines"].checked else "not_published"}


# ---------------- GRE / GMAT decision ----------------
NO_SCORE_STATUSES = {"not_started", "preparing", "unknown"}


def test_policy(store: EvidenceStore, program_id: str) -> dict:
    """The program's verified test policy with its official evidence (excerpt, page, checked date) — nothing inferred."""
    try:
        f = store.get_fact(program_id, "test_policy")
    except EvidenceNotFoundError:
        return {"status": "not_in_store"}
    if f.status != "verified":
        return {"status": "unknown"}
    return {"status": "verified", "summary": f.value,
            "evidence": [{k: e.get(k) for k in ("evidence_id", "excerpt", "excerpt_is_paraphrase", "source_url", "source_title",
                                                "publisher", "checked_on")} for e in f.evidence]}


def test_decision(profile: ApplicantProfile, report: dict) -> dict:
    """Computed in code, not by the model: without a diagnostic score there is nothing to compare, so the state is
    'undecided_no_diagnostic' whatever the planner wrote. No score predictions or admission odds are produced."""
    status = profile.test_status.value
    has_score = profile.test_score is not None and status not in NO_SCORE_STATUSES
    tg = (report.get("strategy") or {}).get("test_guidance") or {}
    return {"state": "has_score" if has_score else "undecided_no_diagnostic", "test_status": status,
            "test_score": profile.test_score if has_score else None,
            "planner_recommendation": tg.get("recommendation"), "planner_rationale": tg.get("rationale")}


# ---------------- assemble ----------------
def build_dashboard(store: EvidenceStore, profile: ApplicantProfile, report: dict) -> dict:
    programs = []
    for rec in report.get("recommendations", []):
        loc = _fact(rec, "location")
        programs.append({
            "program_id": rec["program_id"], "program_name": rec["program_name"],
            "location": (f"{loc['value']['city']}, {loc['value']['state']}" if _verified(loc) else None),
            "fit": program_fit(rec), "affordability": affordability(profile, rec), "feasibility": feasibility(rec, profile) if profile.needs_us_work_authorization is not False else None,
            "deadlines": deadlines(store, rec["program_id"]),
            "test_policy": test_policy(store, rec["program_id"]),
        })
    return {"pathway": pathway(profile, report), "programs": programs, "workspace": workspace(report),
            "test_decision": test_decision(profile, report),
            "international_layer": profile.needs_us_work_authorization is not False,
            "run": {"run_id": report.get("run_id"), "status": report.get("status"), "model": report.get("model")}}
