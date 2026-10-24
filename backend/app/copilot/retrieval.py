"""Deterministic retrieval over the evidence store. No model involved: the same question + context always yields the
same evidence. Only these items (and their ids) are ever shown to the model, and only their ids can be cited."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..tools.evidence_store import EvidenceNotFoundError, EvidenceStore

ID_RE = re.compile(r"^[a-z0-9-]{1,80}$")
MAX_FACTS = 40
EXCERPT_CHARS = 280

# topic keywords -> facts
TOPICS: dict[str, tuple[re.Pattern, tuple[str, ...]]] = {
    "stem": (re.compile(r"\bstem\b|\bopt\b", re.I), ("stem_designation",)),
    "visa": (re.compile(r"\bvisa|sponsor|h-?1b|work (authori[sz]ation|permit)|immigra|international (student|outcome|employment)", re.I),
             ("sponsorship", "international_employment", "stem_designation")),
    "cost": (re.compile(r"\bcost|tuition|afford|budget|expens|price|fees?\b|\$", re.I), ("cost_of_attendance", "tuition")),
    "outcomes": (re.compile(r"salar|employ|outcome|job|placement|hired|recruit", re.I), ("employment_rate", "median_base_salary", "international_employment")),
    "tests": (re.compile(r"\bgmat|\bgre\b|test|exam|score|waiver|requirement|essay|recommendation", re.I), ("test_policy", "application_requirements")),
    "deadlines": (re.compile(r"deadline|round|due date|when (do|should) i apply|apply by", re.I), ("application_deadlines",)),
    "profile": (re.compile(r"class (profile|size)|median gmat|average gmat|gmat (average|median)|how many students|international students|cohort", re.I), ()),
    "scholarships": (re.compile(r"scholarship|fellowship|merit aid|financial aid|funding", re.I), ()),
    "next": (re.compile(r"\bnext\b|\bplan\b|roadmap|where (do|should) i start|prepare|to-?do|priorit", re.I), ("application_deadlines", "test_policy")),
    "format": (re.compile(r"how long|duration|months|years? long|format|location|where is|city", re.I), ("duration_months", "location")),
}
OVERVIEW_FACTS = ("location", "cost_of_attendance", "tuition", "stem_designation", "test_policy", "employment_rate",
                  "median_base_salary", "sponsorship")
ALL_PROGRAMS = re.compile(r"\b(which|what|any|all|every|list|compare all|how many)\b.{0,40}\b(programs?|schools?|mbas?)\b", re.I)
GENERIC = {"school", "business", "management", "university", "college", "graduate", "the", "of", "and", "at", "in", "mba", "full",
           "time", "full-time", "program", "institute", "technology", "new", "york", "state", "southern", "north", "carolina",
           "california", "texas", "daytime", "two-year", "for", "los", "angeles", "san", "saint", "st", "a&m", "michael", "hill", "chapel",
           "notre", "dame", "massachusetts", "carnegie", "mellon"}
EXTRA_ALIASES = {"mit-sloan-mba": ["mit"], "nyu-stern-mba": ["nyu"], "ucla-anderson-mba": ["ucla"], "cmu-tepper-mba": ["cmu", "carnegie mellon"],
                 "unc-kenan-flagler-mba": ["unc", "kenan-flagler", "kenan flagler"], "ut-mccombs-mba": ["ut austin", "ut-austin", "mccombs"],
                 "usc-marshall-mba": ["usc"], "penn-wharton-mba": ["wharton", "penn"], "harvard-hbs-mba": ["hbs", "harvard"],
                 "stanford-gsb-mba": ["gsb", "stanford"], "uva-darden-mba": ["uva", "darden"], "texas-am-mays-mba": ["texas a&m", "mays"],
                 "notre-dame-mendoza-mba": ["notre dame"], "unc-kenan-flagler-mba": ["unc", "kenan-flagler", "kenan flagler", "chapel hill"]}


@dataclass
class Retrieved:
    program_ids: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    facts: list[dict] = field(default_factory=list)          # what the model sees
    evidence_ids: list[str] = field(default_factory=list)     # the only ids that may be cited
    scope_note: str = ""


def aliases(store: EvidenceStore) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for p in store.list_programs():
        words = set()
        for name in (p["school"], p["university"]):
            for w in re.findall(r"[A-Za-z&'-]+", name.lower()):
                if len(w) >= 3 and w not in GENERIC:
                    words.add(w)
        words.update(EXTRA_ALIASES.get(p["program_id"], []))
        out[p["program_id"]] = sorted(words)
    return out


def mentioned_programs(store: EvidenceStore, text: str) -> list[str]:
    t = text.lower()
    hits = []
    for pid, words in aliases(store).items():
        if any(re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", t) for w in words):
            hits.append(pid)
    return hits


def detect_topics(text: str) -> list[str]:
    return [k for k, (pat, _) in TOPICS.items() if pat.search(text)]


def _fmt_value(v):
    if isinstance(v, dict):
        return {k: v[k] for k in list(v)[:6]}
    if isinstance(v, list):
        return v[:6]
    return v


def fact_entry(store: EvidenceStore, pid: str, name: str) -> dict:
    prog = store.get_program(pid)
    f = store.get_fact(pid, name)
    base = {"program_id": pid, "program": prog.school, "fact": name}
    if f.status != "verified":
        return {**base, "status": "unknown", "checked": prog.facts[name].checked, "note": (f.note or "")[:200]}
    ev = f.evidence[0] if f.evidence else {}
    return {**base, "status": "verified", "evidence_id": ev.get("evidence_id"), "value": _fmt_value(f.value), "period": f.period,
            "definition": (f.definition or "")[:200] or None, "excerpt": (ev.get("excerpt") or "")[:EXCERPT_CHARS],
            "source_title": ev.get("source_title"), "source_url": ev.get("source_url")}


def retrieve(store: EvidenceStore, question: str, *, program_id: str | None = None, compare_ids: list[str] | None = None,
             shortlist: list[str] | None = None, follow_up_text: str = "") -> Retrieved:
    """program_id/compare_ids come from explicit UI scope; shortlist from the saved analysis when it is in scope.
    follow_up_text = recent user turns, so "and Booth?" or "what about cost?" keeps context."""
    known = {p["program_id"] for p in store.list_programs()}
    r = Retrieved()
    r.topics = detect_topics(question) or detect_topics(follow_up_text)
    named = mentioned_programs(store, question)
    scoped = [x for x in [program_id, *(compare_ids or [])] if x and ID_RE.match(x) and x in known]
    prev_named = mentioned_programs(store, follow_up_text) if follow_up_text else []
    if named:
        pids = named
    elif prev_named:                     # "what about cost?" continues the schools named in the previous question
        pids = prev_named
    elif scoped:
        pids = scoped
    elif ALL_PROGRAMS.search(question) and r.topics:
        pids = sorted(known)
    elif shortlist:
        pids = [x for x in shortlist if x in known]
    else:
        pids = [x for x in mentioned_programs(store, follow_up_text)]
    if not named and not scoped and pids and shortlist and pids == [x for x in shortlist if x in known]:
        r.scope_note = "No school was named, so the saved analysis's shortlist is used."
    facts_wanted = []
    for t in r.topics:
        facts_wanted += [f for f in TOPICS[t][1] if f not in facts_wanted]
    if not facts_wanted:
        facts_wanted = list(OVERVIEW_FACTS)
    if len(pids) > 6:   # all-program questions: only the topic's facts
        facts_wanted = facts_wanted[:2]
    r.program_ids = pids
    for pid in pids:
        for name in facts_wanted:
            if len(r.facts) >= MAX_FACTS:
                break
            try:
                e = fact_entry(store, pid, name)
            except EvidenceNotFoundError:
                continue
            r.facts.append(e)
            if e.get("evidence_id"):
                r.evidence_ids.append(e["evidence_id"])
    # supplementary validated facts (official extras + third-party figures, each labeled with its source type and kind)
    supp_fields: list[str] = []
    for t in r.topics or ["overview"]:
        supp_fields += [f for f in SUPP_TOPICS.get(t, ()) if f not in supp_fields]
    if len(pids) > 6:
        supp_fields = supp_fields[:1]
    if "visa" in r.topics:
        from ..tools.sponsorship import SPONSORSHIP_NOTE, employer_filings, get_sponsorship_evidence, metro_for, mentioned_employers, occupation_for
        occ, met = occupation_for(question + " " + follow_up_text), metro_for(question)
        for emp in mentioned_employers(question)[:2]:
            for row in employer_filings(emp, occ, met)[:4]:
                r.facts.append({"program_id": None, "program": emp, "fact": "historical_h1b_filings", "status": "verified",
                                "evidence_id": row["evidence_id"], "value": {"employer": emp, "occupation": row["occupation"], "metro": row["metro"],
                                "filings": row["filings"], "median_annual_wage": row["median_annual_wage"]}, "period": f"FY{row['fiscal_year']}",
                                "source_type": "official", "value_kind": "published", "publisher": "U.S. Department of Labor (OFLC LCA disclosure data)",
                                "label": "HISTORICAL employer filings, not a promise of sponsorship", "notes": SPONSORSHIP_NOTE})
                r.evidence_ids.append(row["evidence_id"])
        for pid in pids[:4]:
            ev = get_sponsorship_evidence(pid, occ, met)
            for e in [x for x in ev["employers"] if x["total_filings"]][:5]:
                for row in e["filings"][:2]:
                    r.facts.append({"program_id": pid, "program": pid, "fact": "historical_h1b_filings", "status": "verified",
                                    "evidence_id": row["evidence_id"], "value": {"employer": e["employer"], "occupation": row["occupation"],
                                    "metro": row["metro"], "filings": row["filings"], "median_annual_wage": row["median_annual_wage"]},
                                    "period": f"FY{row['fiscal_year']}", "source_type": "official", "value_kind": "published",
                                    "publisher": "U.S. Department of Labor (OFLC LCA disclosure data)",
                                    "label": "HISTORICAL employer filings, not a promise of sponsorship", "notes": SPONSORSHIP_NOTE})
                    r.evidence_ids.append(row["evidence_id"])
    from ..tools import supplementary as supp
    for pid in pids:
        for f in supp.verified(pid):
            if f.field in supp_fields and len(r.facts) < MAX_FACTS + 20:
                r.facts.append(supp_entry(store, f))
                r.evidence_ids.append(f.fact_id)
    return r


SUPP_TOPICS = {
    "cost": ("cost_of_attendance", "mandatory_fees", "tuition", "tuition_and_fees", "est_annual_cost", "est_two_year_cost", "reported_cost_of_attendance"),
    "tests": ("class_median_gmat", "class_avg_gmat"),
    "profile": ("class_size", "class_median_gmat", "class_avg_gmat", "class_pct_international"),
    "scholarships": ("scholarships",),
    "deadlines": ("application_deadlines",),
    "next": ("application_deadlines",),
    "visa": ("class_pct_international",),
    "overview": ("est_annual_cost", "class_size", "application_deadlines"),
}


def supp_entry(store: EvidenceStore, f) -> dict:
    try:
        school = store.get_program(f.program_id).school
    except EvidenceNotFoundError:
        school = f.program_id
    kind = {"published": "official published value", "reported": f"school figure as reported by {f.publisher}",
            "estimate": f"ESTIMATE by {f.publisher} (not an official cost)"}[f.value_kind] if f.source_type == "secondary" or f.value_kind != "published" \
        else "official published value"
    return {"program_id": f.program_id, "program": school, "fact": f.field, "status": "verified", "evidence_id": f.fact_id,
            "value": f.value, "period": f.period, "period_basis": f.period_basis, "source_type": f.source_type, "value_kind": f.value_kind,
            "publisher": f.publisher, "label": kind, "notes": f.notes[:200], "source_url": f.source_url}
