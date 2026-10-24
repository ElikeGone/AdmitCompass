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


# ---------------- weekly action system ----------------
# The Strategy Planner writes weekly actions as plain sentences (all "high" priority in practice). This layer is
# deterministic code: a fixed keyword table gives each action a category, which sets its tier (must / should /
# optional), a planning-estimate duration and a reason. Reasons cite facts already on the dashboard where they exist.
# Nothing here is produced by a model, and the durations are labeled as AdmitCompass planning estimates in the UI.
ACTION_RULES: list[tuple[str, str, str, int]] = [   # (regex, category, tier, minutes) — first match wins; order matters
    (r"timed practice test", "test_practice", "must", 165),
    (r"select gmat or gre|decide whether (?:the current test plan|to sit)", "test_decision", "must", 30),
    (r"diagnostic", "test_diagnostic", "must", 165),
    (r"selected test", "test_booking", "must", 30),
    (r"recommend", "recommenders", "must", 30),
    (r"reviewer|critique", "review", "should", 30),
    (r"school list", "shortlist", "must", 45),
    (r"submit|submission|confirmations", "submission", "must", 60),
    (r"deadline", "deadlines", "must", 30),
    (r"cost|financ|budget", "cost", "must", 45),
    (r"career.?story|narrative|essay|short answers|examples demonstrating", "story", "must", 60),
    (r"test.?prep|exam prep|study plan|weakest sections|review errors", "test_prep", "should", 90),
    (r"test policies|requirements|application components|official checklist|portals|official instructions", "requirements", "should", 30),
    (r"resume", "resume", "should", 60),
    (r"transcript", "transcripts", "should", 30),
    (r"dso|immigration", "immigration", "should", 30),
    (r"recruiting|international employment", "school_questions", "optional", 30),
]
WEEK_ONE_ESSENTIALS = ["test_diagnostic", "story", "deadlines", "cost", "recommenders"]
MAX_PRIORITY_ACTIONS = 5
TIER_ORDER = {"must": 0, "should": 1, "optional": 2}
GENERIC_WHY = {
    "test_decision": "Turns your practice results into one test choice, so preparation time goes to a single exam.",
    "test_practice": "A full timed test is the only reliable check of whether preparation is working.",
    "test_prep": "Steady preparation in your available hours is what moves a practice score.",
    "submission": "Applications are only complete once every component is in before the deadline.",
    "test_booking": "Test dates and official score reports must fit before your target round.",
    "deadlines": "Every other step is scheduled backwards from the round you choose.",
    "cost": "Your budget can only be checked against an official total cost of attendance.",
    "recommenders": "Recommenders need time and context to write detailed letters; early conversations protect quality.",
    "story": "Your essays and interviews depend on a clear reason for the career change.",
    "shortlist": "A final list keeps your effort on programs that fit your career goal and budget.",
    "requirements": "Official requirements decide what you must prepare; they can change between cycles.",
    "resume": "Your resume is the evidence behind the career story and recommender briefs.",
    "transcripts": "Official transcripts and translations can take weeks to arrive.",
    "immigration": "Personal immigration questions need a qualified answer, not general guidance.",
    "review": "An outside reader catches gaps you can no longer see.",
    "school_questions": "Useful context from the schools, but your plan doesn't depend on it this week.",
    "other": "Part of the Strategy Planner's plan for this period.",
}


def classify_action(text: str) -> tuple[str, str, int]:
    t = text.lower()
    for rx, cat, tier, minutes in ACTION_RULES:
        if re.search(rx, t):
            return cat, tier, minutes
    return "other", "should", 45


def _why(cat: str, profile: ApplicantProfile | None, programs: list[dict], gaps: list[dict], test_state: str | None) -> str:
    if cat == "test_diagnostic" and test_state == "undecided_no_diagnostic":
        return "There's no diagnostic score in your profile, so the GRE-or-GMAT choice can't be made yet (see section 2)."
    if cat == "cost":
        missing = [p["program_name"] for p in programs if p.get("affordability") and not p["affordability"].get("comparable")]
        if missing:
            return f"No official total cost is on file for {', '.join(missing)}, so your budget can't be checked against it yet."
    if cat == "story":
        g = next((g for g in gaps if re.search(r"narrative|story|transition", g.get("gap", ""), re.I)), None)
        if g:
            return f"Gap flagged by the Strategy Planner (AI-inferred): {g['gap']}"
    if cat == "recommenders":
        g = next((g for g in gaps if re.search(r"recommend", g.get("gap", ""), re.I)), None)
        if g:
            return f"Gap flagged by the Strategy Planner (AI-inferred): {g['gap']}"
    if cat == "test_prep" and profile is not None and profile.hours_per_week_available:
        return f"Steady preparation within your {profile.hours_per_week_available} available hours a week is what moves a practice score."
    return GENERIC_WHY[cat]


def weekly_actions(tasks: list[dict], profile: ApplicantProfile | None = None, programs: list[dict] | None = None,
                   gaps: list[dict] | None = None, test_state: str | None = None) -> dict:
    """Per-week priority actions (at most 5 must/should, plus optional), with tier, minutes and reason per action.
    Week 1 always covers the essentials: the earliest action of each essential category is moved up if needed."""
    programs, gaps = programs or [], gaps or []
    actions, week_of = {}, {}
    for t in tasks:
        cat, tier, minutes = classify_action(t["text"])
        actions[t["id"]] = {"category": cat, "tier": tier, "minutes": minutes, "why": _why(cat, profile, programs, gaps, test_state),
                            "plan_week": t["week"], "moved_from": None}
        week_of[t["id"]] = t["week"]
    if tasks:
        first = min(week_of.values())
        for cat in WEEK_ONE_ESSENTIALS:
            ids = [t["id"] for t in tasks if actions[t["id"]]["category"] == cat]
            if ids and not any(week_of[i] == first for i in ids):
                earliest = min(ids, key=lambda i: (week_of[i], i))
                actions[earliest]["moved_from"] = week_of[earliest]
                week_of[earliest] = first
                actions[earliest]["tier"] = "must"
    weeks = []
    for w in sorted(set(week_of.values())):
        ids = [t["id"] for t in tasks if week_of[t["id"]] == w]
        pos = {i: n for n, i in enumerate(ids)}   # plan order breaks ties within a tier
        ids = sorted(ids, key=lambda i: (TIER_ORDER[actions[i]["tier"]], pos[i]))
        prio = [i for i in ids if actions[i]["tier"] != "optional"]
        weeks.append({"week": w, "priority": prio[:MAX_PRIORITY_ACTIONS],
                      "optional": [i for i in ids if actions[i]["tier"] == "optional"],
                      "more": prio[MAX_PRIORITY_ACTIONS:],
                      "minutes": sum(actions[i]["minutes"] for i in prio[:MAX_PRIORITY_ACTIONS])})
    return {"weeks": weeks, "actions": actions,
            "estimate_note": "Minutes are AdmitCompass planning estimates for each kind of task, not figures from the schools or test makers."}


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
    ws, td, pw = workspace(report), test_decision(profile, report), pathway(profile, report)
    ws["weekly"] = weekly_actions(ws["tasks"], profile, programs, pw.get("gaps"), td["state"])
    return {"pathway": pw, "programs": programs, "workspace": ws,
            "test_decision": td,
            "international_layer": profile.needs_us_work_authorization is not False,
            "run": {"run_id": report.get("run_id"), "status": report.get("status"), "model": report.get("model")}}
