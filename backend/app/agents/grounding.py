"""Deterministic grounding checks and fail-closed sanitizers for agent outputs.

The model can reason and explain; only the evidence store can establish facts. These checks run
in code after every agent output, independent of what the prompt said.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from ..schemas.agents import (
    EvidenceOutput, GroundingViolation, PathwayOutput, SkepticOutput, StrategyOutput,
)
from ..schemas.applicant import ApplicantProfile
from ..schemas.claims import Claim, ClaimLabel
from ..tools.agent_tools import compare_metrics
from ..tools.evidence_store import EvidenceNotFoundError, EvidenceStore

NEGATIONS = re.compile(r"\b(no|not|never|cannot|can't|without|isn't|aren't|won't|nor|unable|neither)\b|n't\b", re.I)
RISKY_PATTERNS = {
    "scholarship_odds": re.compile(r"\b(chances?|odds|probability|likelihood)\s+of\s+(receiving\s+|getting\s+|winning\s+)?(an?\s+)?(scholarship|fellowship|merit aid|financial aid|funding)"
                                   r"|\b(likely|unlikely|guaranteed)\s+to\s+(receive|get|win)\s+(an?\s+)?(scholarship|fellowship|merit aid)", re.I),
    "admission_odds": re.compile(r"\b(chances?|odds|probability|likelihood)\s+of\s+(admission|admit|being admitted|acceptance|getting in)\b"
                                 r"|\b\d{1,3}\s*%\s*(chance|probability|likelihood)", re.I),
    "guarantee": re.compile(r"\bguarantee[sd]?\b", re.I),
    "visa_eligibility_assertion": re.compile(
        r"\b(you|applicant|they|graduates?)\s+(are|is|will be|would be)\s+eligible\s+for\s+(an?\s+)?(h-?1b|opt|stem opt|visa|work authorization)"
        r"|\b(will|would)\s+sponsor\b", re.I),
    # Past LCA filings are history about an employer, never a promise about a person or role.
    "sponsorship_guarantee": re.compile(
        r"\b(will|would|is going to|are going to)\s+(definitely\s+|likely\s+|probably\s+|certainly\s+)?(sponsor|file\s+(an?\s+)?h-?1b|support\s+(your|a)\s+visa)"
        r"|\b(is|are)\s+(sure|certain|guaranteed|likely|expected)\s+to\s+sponsor"
        r"|\b(always|reliably|routinely|consistently)\s+sponsors?\b"
        r"|\bsponsors?\s+(visas?|h-?1bs?)\s+for\s+(all|every|any|its)\b"
        r"|\b(you|graduates?|applicants?|students?)\s+(can|will|would)\s+(get|obtain|receive|secure)\s+(an?\s+)?(h-?1b|visa|sponsorship|work authorization)"
        r"|\b(secures?|ensures?|assures?)\s+(your\s+)?(h-?1b|visa|sponsorship|work authorization)", re.I),
}
CALENDAR_DATE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(st|nd|rd|th)?\b|\b20\d\d-\d\d-\d\d\b", re.I)
# Negation/hedge that FOLLOWS the risky word in the same clause, e.g.
# "any implication of guaranteed immigration benefit ... is unsupported" (a correct warning).
NEGATION_AFTER = re.compile(r"^[^.;!?]{0,80}?\b(is|are|was|were|be|remains?)\s+(not|never|unsupported|unverified|unknown|"
                            r"not\s+established|not\s+supported)\b|^[^.;!?]{0,80}?\b(unsupported|unverified)\b", re.I)
# Topics whose verified claims must cite evidence for that same fact type.
TOPIC_FACTS = {
    "sponsorship": (re.compile(r"\b(sponsor\w*|h-?1b|visa)\b", re.I), {"sponsorship"}),
    "stem": (re.compile(r"\bstem\b", re.I), {"stem_designation"}),
}
TOPIC_HEDGE = re.compile(r"\b(unknown|not\s+(found|established|verified|available|published|stated)|no\s+(\w+\s+){0,3}"
                         r"(evidence|statistics|information|data)|unverified|cannot\s+be\s+(confirmed|determined)|"
                         r"confirm|does\s+not|do\s+not|is\s+not|are\s+not|isn't|aren't|neither|nor)\b", re.I)
NUMBER = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*([kK]\b)?")


# ---------- helpers ----------
def iter_strings(obj: Any, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_strings(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from iter_strings(v, f"{path}[{i}]")


NEGATED_AS = re.compile(r"\b(do not|don't|does not|doesn't|never|not|cannot|can't)\b[^.;!?]*\b(as|is|are|be|mean|imply)\s+(an?\s+|any\s+)?$", re.I)


def risky_language(text: str) -> list[str]:
    hits = []
    for rule, pat in RISKY_PATTERNS.items():
        for m in pat.finditer(text):
            # negation must be in the same clause: "It is not cheap, but it guarantees a job" is still a guarantee
            window = re.split(r"[.;!?]|\bbut\b|\bhowever\b|\byet\b", text[max(0, m.start() - 40):m.start()], flags=re.I)[-1]
            # "Do not treat historical filings as a guarantee": negated framing earlier in the same sentence
            clause = re.split(r"[.;!?]", text[max(0, m.start() - 160):m.start()])[-1]
            negated_as = NEGATED_AS.search(clause)
            if not NEGATIONS.search(window) and not NEGATION_AFTER.search(text[m.end():]) and not negated_as:
                hits.append(rule)
                break
    return hits


SHORT_ACADEMIC_YEAR = re.compile(r"\b(\d{2})(\d{2})\s*[-–/]\s*(\d{2})\b(?!\d)")


def numbers_in(text: str) -> set[float]:
    out = set()
    # "2026-27" -> "2026-2027" so the short year isn't read as the number 27
    text = SHORT_ACADEMIC_YEAR.sub(lambda m: f"{m.group(1)}{m.group(2)}-{m.group(1)}{m.group(3)}", text or "")
    for m in NUMBER.finditer(text):
        try:
            v = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        out.add(v * 1000 if m.group(2) else v)
    return out


def _numbers_from_value(v: Any) -> set[float]:
    if isinstance(v, bool):
        return set()
    if isinstance(v, (int, float)):
        return {float(v)}
    if isinstance(v, str):
        return numbers_in(v)
    if isinstance(v, dict):
        return set().union(*(_numbers_from_value(x) for x in v.values()), *(numbers_in(k) for k in v)) if v else set()
    if isinstance(v, list):
        return set().union(*(_numbers_from_value(x) for x in v)) if v else set()
    return set()


def external_evidence(eid: str) -> dict | None:
    """lca-... (DOL LCA filings) and sx-... (validated supplementary facts) evidence ids; None if unknown."""
    if eid.startswith("lca-"):
        from ..tools.sponsorship import resolve
        r = resolve(eid)
        return None if r is None else {"fact": "sponsorship", "program_id": None,
                                       "numbers": _numbers_from_value({k: r[k] for k in ("filings", "worker_positions", "median_annual_wage", "fiscal_year")})}
    if eid.startswith("sx-"):
        from ..tools.supplementary import by_id
        f = by_id(eid)
        return None if f is None else {"fact": f.field, "program_id": f.program_id,
                                       "numbers": _numbers_from_value(f.value) | numbers_in(f.period or "")}
    return None


def supported_numbers(store: EvidenceStore, evidence_ids: list[str]) -> set[float]:
    allowed: set[float] = set()
    for eid in evidence_ids:
        if eid.startswith(("lca-", "sx-")):
            ext = external_evidence(eid)
            allowed |= ext["numbers"] if ext else set()
            continue
        pid, name = store.fact_for_evidence(eid)
        f = store.get_fact(pid, name)
        allowed |= _numbers_from_value(f.value) | numbers_in(f.period or "") | numbers_in(f.definition or "")
        allowed |= numbers_in(store.get_evidence(eid)["excerpt"])
    return allowed


def profile_numbers(profile: ApplicantProfile | None) -> set[float]:
    """Numbers the applicant supplied (budget, score, hours...) may be restated in claims."""
    return _numbers_from_value(profile.known_fields()) if profile else set()


def check_claim(store: EvidenceStore, claim: Claim, program_id: str | None = None,
                extra_allowed: set[float] | None = None) -> list[str]:
    """Return problems with a claim (empty list = grounded). extra_allowed = numbers from the applicant profile."""
    problems = []
    for eid in claim.evidence_ids:
        if eid.startswith(("lca-", "sx-")):
            ext = external_evidence(eid)
            if ext is None:
                problems.append(f"evidence id {eid!r} does not exist")
            elif program_id and ext.get("program_id") and ext["program_id"] != program_id:
                problems.append(f"evidence {eid!r} belongs to {ext['program_id']}, not {program_id}")
            continue
        try:
            pid, _ = store.fact_for_evidence(eid)
        except EvidenceNotFoundError:
            problems.append(f"evidence id {eid!r} does not exist")
            continue
        if program_id and pid != program_id:
            problems.append(f"evidence {eid!r} belongs to {pid}, not {program_id}")
    if claim.label is ClaimLabel.VERIFIED_FACT:
        if not claim.evidence_ids:
            problems.append("verified_fact without evidence_ids from the store")
        elif not problems:
            cited = {store.fact_for_evidence(e)[1] if not e.startswith(("lca-", "sx-")) else external_evidence(e)["fact"]
                     for e in claim.evidence_ids}
            sentences = re.split(r"(?<=[.;!?])\s+", claim.text)
            for topic, (pat, facts) in TOPIC_FACTS.items():
                # Only assertive sentences count: "sponsorship evidence is unknown" is a correct, hedged statement.
                assertive = [s for s in sentences if pat.search(s) and not TOPIC_HEDGE.search(s)]
                if assertive and not (cited & facts):
                    problems.append(f"{topic} claim must cite {sorted(facts)} evidence; cited {sorted(cited)}")
        if claim.label is ClaimLabel.VERIFIED_FACT and claim.evidence_ids and not problems:
            allowed = supported_numbers(store, claim.evidence_ids) | (extra_allowed or set())
            unsupported = [n for n in numbers_in(claim.text) if n >= 10 and n not in allowed]
            if unsupported:
                problems.append(f"numbers {sorted(unsupported)} not found in cited evidence")
    return problems


def expected_affordability(store: EvidenceStore, profile: ApplicantProfile, pid: str) -> str:
    f = store.get_fact(pid, "cost_of_attendance")
    if f.status != "verified" or profile.max_total_budget_usd_per_year is None:
        return "unknown"
    return "within_budget" if f.value <= profile.max_total_budget_usd_per_year else "over_budget"


def affordability_basis(store: EvidenceStore, profile: ApplicantProfile, pid: str) -> str:
    """Deterministic explanation used whenever the model's affordability is corrected."""
    f = store.get_fact(pid, "cost_of_attendance")
    if f.status != "verified":
        return "Unknown: the program's total cost of attendance is not verified (tuition alone is not total cost)."
    if profile.budget_period == "total_program":
        return (f"Unknown: your budget is for the whole program, but the published cost of attendance "
                f"(${f.value:,.0f}, {f.period}) covers one academic year, so they can't be compared safely.")
    if profile.max_total_budget_usd_per_year is None:
        return "Unknown: no budget was provided."
    rel = "within" if f.value <= profile.max_total_budget_usd_per_year else "over"
    return (f"Published cost of attendance ${f.value:,.0f} ({f.period}) is {rel} your per-year budget "
            f"of ${profile.max_total_budget_usd_per_year:,.0f}.")


def expected_stem(store: EvidenceStore, pid: str) -> str:
    f = store.get_fact(pid, "stem_designation")
    if f.status != "verified":
        return "unknown"
    return "verified_designated" if f.value["designated"] else "verified_not_designated"


def expected_sponsorship(store: EvidenceStore, pid: str) -> str:
    """'employer_specific_evidence' = a verified school sponsorship fact, OR historical DOL H-1B filings by employers that the
    school's official report says hired its graduates. Neither is ever a promise of sponsorship (see sponsorship_guarantee)."""
    if store.get_fact(pid, "sponsorship").status == "verified":
        return "employer_specific_evidence"
    from ..tools.sponsorship import get_sponsorship_evidence
    ev = get_sponsorship_evidence(pid)
    return "employer_specific_evidence" if any(e["total_filings"] for e in ev["employers"]) else "unknown"


def _v(agent: str, rule: str, detail: str, action: str) -> GroundingViolation:
    return GroundingViolation(agent=agent, rule=rule, detail=detail[:400], action=action)


def _text_violations(agent: str, data: dict, action: str, check_dates: bool = False) -> list[GroundingViolation]:
    out = []
    for path, text in iter_strings(data):
        for rule in risky_language(text):
            out.append(_v(agent, rule, f"{path}: {text[:200]}", action))
        if check_dates and CALENDAR_DATE.search(text):
            out.append(_v(agent, "invented_calendar_date", f"{path}: {text[:200]}", action))
    return out


def _clean_claims(store, agent, claims, program_id, violations, path, extra_allowed=None):
    kept = []
    for c in claims:
        probs = check_claim(store, c, program_id, extra_allowed)
        hits = risky_language(c.text)
        if probs or hits:
            violations.append(_v(agent, "unsupported_claim", f"{path}: '{c.text[:150]}' -> {probs + hits}", "dropped claim"))
        else:
            kept.append(c)
    return kept


# ---------- per-agent check + sanitize (returns sanitized output, violations) ----------
def ground_pathway(store: EvidenceStore, out: PathwayOutput) -> tuple[PathwayOutput, list[GroundingViolation]]:
    v: list[GroundingViolation] = []
    known = {p["program_id"] for p in store.list_programs()}
    cands = []
    for c in out.candidates:
        if c.program_id in known:
            cands.append(c)
        else:
            v.append(_v("pathway_matcher", "unknown_program_id", c.program_id, "dropped candidate"))
    excl = [e for e in out.excluded if e.program_id in known]
    claims = _clean_claims(store, "pathway_matcher", out.claims, None, v, "claims")
    data = out.model_copy(update={"candidates": cands, "excluded": excl, "claims": claims})
    for t in _text_violations("pathway_matcher", data.model_dump(exclude={"claims"}), "flagged"):
        v.append(t)
    return data, v


def ground_evidence(store: EvidenceStore, profile: ApplicantProfile, out: EvidenceOutput,
                    candidate_ids: list[str]) -> tuple[EvidenceOutput, list[GroundingViolation]]:
    v: list[GroundingViolation] = []
    dossiers = []
    for d in out.dossiers:
        if d.program_id not in candidate_ids:
            v.append(_v("evidence_analyst", "program_not_in_shortlist", d.program_id, "dropped dossier"))
            continue
        upd: dict[str, Any] = {}
        for field, expected in (("stem_status", expected_stem(store, d.program_id)),
                                ("sponsorship_status", expected_sponsorship(store, d.program_id)),
                                ("affordability", expected_affordability(store, profile, d.program_id))):
            if getattr(d, field) != expected:
                v.append(_v("evidence_analyst", f"{field}_mismatch",
                            f"{d.program_id}: model said {getattr(d, field)!r}, store says {expected!r}",
                            f"corrected to {expected!r}"))
                upd[field] = expected
                if field == "affordability":
                    upd["affordability_basis"] = affordability_basis(store, profile, d.program_id)
        upd["claims"] = _clean_claims(store, "evidence_analyst", d.claims, d.program_id, v, f"dossier[{d.program_id}]",
                                      profile_numbers(profile))
        dossiers.append(d.model_copy(update=upd))
    comps = []
    for c in out.metric_comparisons:
        ids = [i for i in c.program_ids if i in candidate_ids]
        if len(ids) < 2:
            continue
        truth = compare_metrics(store, ids, c.metric)["all_comparable"]
        if c.treated_as_comparable != truth:
            v.append(_v("evidence_analyst", "incomparable_metrics",
                        f"{c.metric} for {ids}: model treated_as_comparable={c.treated_as_comparable}, rule says {truth}",
                        f"corrected to {truth}"))
        comps.append(c.model_copy(update={"program_ids": ids, "treated_as_comparable": truth}))
    data = out.model_copy(update={"dossiers": dossiers, "metric_comparisons": comps})
    v += _text_violations("evidence_analyst", data.model_dump(exclude={"dossiers": {"__all__": {"claims"}}}), "flagged")
    return data, v


def ground_strategy(store: EvidenceStore, out: StrategyOutput) -> tuple[StrategyOutput, list[GroundingViolation]]:
    v: list[GroundingViolation] = []
    tg_ids = []
    for eid in out.test_guidance.evidence_ids:
        try:
            store.fact_for_evidence(eid)
            tg_ids.append(eid)
        except EvidenceNotFoundError:
            v.append(_v("strategy_planner", "unknown_evidence_id", eid, "removed id"))
    claims = _clean_claims(store, "strategy_planner", out.claims, None, v, "claims")
    data = out.model_copy(update={"claims": claims,
                                  "test_guidance": out.test_guidance.model_copy(update={"evidence_ids": tg_ids})})
    # Fail closed on invented dates / risky language: drop offending plan items.
    week_plan = []
    for w in data.weekly_plan:
        acts = [a for a in w.actions if not (risky_language(a) or CALENDAR_DATE.search(a))]
        if len(acts) != len(w.actions):
            v.append(_v("strategy_planner", "risky_or_dated_action", f"week {w.week}", "dropped action(s)"))
        if acts:
            week_plan.append(w.model_copy(update={"actions": acts}))
    roadmap = []
    for r in data.roadmap:
        ms = [m for m in r.milestones if not (risky_language(m) or CALENDAR_DATE.search(m))]
        if len(ms) != len(r.milestones) or CALENDAR_DATE.search(r.timing):
            v.append(_v("strategy_planner", "risky_or_dated_milestone", r.phase, "dropped milestone(s)/date"))
        if ms:
            roadmap.append(r.model_copy(update={"milestones": ms,
                                                 "timing": CALENDAR_DATE.sub("[date removed]", r.timing)}))
    data = data.model_copy(update={"weekly_plan": week_plan or data.weekly_plan[:0], "roadmap": roadmap})
    v += _text_violations("strategy_planner", data.model_dump(exclude={"claims", "weekly_plan", "roadmap"}),
                          "flagged", check_dates=True)
    return data, v


def ground_skeptic(out: SkepticOutput, revisions_left: int) -> tuple[SkepticOutput, list[GroundingViolation]]:
    v = []
    if out.revision_request and revisions_left <= 0:
        v.append(_v("skeptic", "revision_limit", out.revision_request.target_agent, "revision request ignored"))
        out = out.model_copy(update={"revision_request": None})
    return out, v


def is_blocking(violations: list[GroundingViolation]) -> bool:
    """Violations worth one retry of the agent before sanitizing."""
    return any(x.rule in {"unknown_program_id", "unsupported_claim", "unknown_evidence_id"} for x in violations)
