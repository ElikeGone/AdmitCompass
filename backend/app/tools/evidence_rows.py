"""Evidence behind each shortlisted program, one row per important claim.

Every row is built in code from the evidence store (official facts) or the supplementary layer (third-party estimates):
claim, status, source title, source URL, date checked, data period, freshness warning and a short tradeoff.
Statuses:
  verified                  quoted from an official page (or re-checked first-hand)
  source-backed paraphrase  an official page says it, but our excerpt is a paraphrase
  estimated                 a third-party estimate, never the school's own figure
  unknown                   not established from the official pages checked; nothing is guessed
"""
from __future__ import annotations

from typing import Any

from .evidence_store import EvidenceNotFoundError, EvidenceStore
from .supplementary import verified as supp_verified

STATUS_FROM_LEVEL = {"rechecked_first_hand": "verified", "source_backed_excerpt": "verified",
                     "source_backed_paraphrase": "source-backed paraphrase"}

LABEL = {"cost_of_attendance": "Cost of attendance", "tuition": "Tuition", "stem_designation": "STEM designation",
         "employment_rate": "Employment rate", "median_base_salary": "Median base salary", "test_policy": "Test policy",
         "application_deadlines": "Application deadlines", "international_employment": "International student outcomes",
         "sponsorship": "School-level visa sponsorship"}

TRADEOFF = {
    "cost_of_attendance": "Excludes scholarships and aid; living costs depend on your choices.",
    "cost_estimate": "A third-party estimate, not the school's figure — use it only until an official total is published.",
    "tuition": "Tuition only: leaves out fees, insurance and living costs.",
    "stem_designation": "A program classification that matters for post-study work options — not evidence that any employer will sponsor a visa.",
    "employment_rate": "School-reported; cohorts and definitions differ between schools, so compare with care.",
    "median_base_salary": "A median of graduates who reported pay; your result depends on function and location.",
    "test_policy": "Policies change between cycles — confirm before you register for a test.",
    "application_deadlines": "Choosing a round trades preparation time against how soon you apply.",
    "international_employment": "Without a published figure, ask the career office for international outcomes.",
    "sponsorship": "Employers, not schools, decide sponsorship case by case; see employer filing history instead.",
}
ORDER = ["cost_of_attendance", "tuition", "stem_designation", "employment_rate", "median_base_salary", "test_policy",
         "application_deadlines", "international_employment", "sponsorship"]


def _money(v: Any) -> str:
    return f"${v:,.0f}" if isinstance(v, (int, float)) else str(v)


def claim_text(fact: str, value: Any, period: str | None) -> str:
    when = f" ({period})" if period else ""
    if fact in ("cost_of_attendance", "tuition", "median_base_salary"):
        per = " per year" if fact != "median_base_salary" else ""
        return f"{LABEL[fact]}: {_money(value)}{per}{when}"
    if fact == "employment_rate":
        return f"{LABEL[fact]}: {value}%{when}"
    if fact == "stem_designation" and isinstance(value, dict):
        return f"STEM-designated: {'yes' if value.get('designated') else 'no'} — {value.get('scope', '')}".rstrip(" —")
    if fact == "application_deadlines" and isinstance(value, list):
        rounds = "; ".join(f"{r.get('round')}: {r.get('deadline')}" for r in value if isinstance(r, dict))
        return f"{LABEL[fact]}{when}: {rounds}"
    if isinstance(value, str):
        return f"{LABEL[fact]}: {value}"
    return f"{LABEL[fact]}: documented"


def _row(fact: str, claim: str, status: str, ev: dict | None, period: str | None, freshness: dict | None,
         tradeoff_key: str | None = None, **extra) -> dict:
    ev = ev or {}
    return {"fact": fact, "claim": claim, "status": status, "source_title": ev.get("source_title"), "source_url": ev.get("source_url"),
            "publisher": ev.get("publisher"), "checked_on": ev.get("checked_on"), "data_period": period,
            # only real staleness is a warning; undated policy facts (STEM, test policy) aren't stale
            "freshness_warning": (freshness or {}).get("warning") if (freshness or {}).get("stale") else None,
            "tradeoff": TRADEOFF[tradeoff_key or fact], **extra}


def evidence_rows(store: EvidenceStore, program_id: str) -> list[dict]:
    rows: list[dict] = []
    try:
        store.get_program(program_id)
    except EvidenceNotFoundError:
        return rows
    supp = supp_verified(program_id)
    for fact in ORDER:
        f = store.get_fact(program_id, fact)
        if f.status == "verified" and f.evidence:
            ev = f.evidence[0]
            rows.append(_row(fact, claim_text(fact, f.value, f.period), STATUS_FROM_LEVEL.get(ev.get("verification_level"), "verified"),
                             ev, f.period, f.freshness, evidence_id=ev.get("evidence_id")))
            continue
        # official supplementary fact (e.g. deadlines published on a page outside the core collection)
        s = next((x for x in supp if x.field == fact and x.source_type == "official"), None)
        if s:
            rows.append(_row(fact, claim_text(fact, s.value, s.period), "verified",
                             {"source_title": s.publisher, "source_url": s.source_url, "publisher": s.publisher, "checked_on": s.retrieved_on},
                             s.period, None, evidence_id=s.fact_id))
            continue
        if fact == "cost_of_attendance":   # no official total: show a labeled third-party estimate when one exists
            est = next((x for x in supp if x.field == "est_annual_cost" and x.value_kind == "estimate"), None)
            if est:
                rows.append(_row(fact, f"Estimated one-year cost: {_money(est.value)} ({est.period}) — by {est.publisher}", "estimated",
                                 {"source_title": est.publisher, "source_url": est.source_url, "publisher": est.publisher, "checked_on": est.retrieved_on},
                                 est.period, None, tradeoff_key="cost_estimate", evidence_id=est.fact_id))
                continue
        rows.append(_row(fact, f"{LABEL[fact]}: not established from the official pages checked", "unknown", None, None, None))
    return rows
