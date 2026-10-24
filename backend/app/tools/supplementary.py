"""Read-side helpers for data/programs/supplementary.json (built and validated by scripts/build_supplementary.py).

Precedence (never mixed into one number):
  1. official cost of attendance — core evidence store, else a validated official supplementary page
  2. tuition (official core value) and mandatory fees (official page, else as reported by Poets&Quants)
  3. Poets&Quants estimated one-year / two-year cost (estimates, 2026-27)
  4. Clear Admit compiled cost of attendance (reported, 2025-26 — one year older)
Only status == "verified" records are ever shown as values; everything else is a research gap with its reason.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

from ..core.config import REPO_ROOT
from ..schemas.supplementary import FIELD_LABEL, SuppFact

PATH = REPO_ROOT / "data" / "programs" / "supplementary.json"
GAP_REASON = {"not_found": "Not stated on the official pages checked", "blocked": "The source blocks automated retrieval",
              "unverified": "Collected, but the value couldn't be confirmed on the live page"}


@lru_cache(maxsize=1)
def load() -> tuple[SuppFact, ...]:
    if not PATH.exists():
        return ()
    return tuple(SuppFact.model_validate(x) for x in json.loads(PATH.read_text(encoding="utf-8"))["facts"])


def reload() -> None:
    load.cache_clear()


def verified(pid: str) -> list[SuppFact]:
    return [f for f in load() if f.program_id == pid and f.status == "verified"]


def by_id(fid: str) -> SuppFact | None:
    return next((f for f in load() if f.fact_id == fid and f.status == "verified"), None)


def label(f: SuppFact) -> str:
    who = "official" if f.source_type == "official" else f.publisher
    kind = {"published": "", "reported": "reported", "estimate": "estimate"}[f.value_kind]
    return f"{FIELD_LABEL[f.field]} ({', '.join(x for x in (who, kind, f.period) if x)})"


def public(f: SuppFact) -> dict:
    return {"fact_id": f.fact_id, "field": f.field, "label": FIELD_LABEL[f.field], "display_label": label(f), "value": f.value,
            "unit": f.unit, "period": f.period, "period_basis": f.period_basis, "source_url": f.source_url, "publisher": f.publisher,
            "source_type": f.source_type, "value_kind": f.value_kind, "retrieved_on": f.retrieved_on, "notes": f.notes}


def research_view(pid: str) -> dict:
    facts = [public(f) for f in verified(pid)]
    have = {(f["field"], f["source_type"]) for f in facts}
    gaps = []
    for f in load():
        gmat_known = any(x[0] in ("class_median_gmat", "class_avg_gmat") for x in have)
        if f.field in ("class_median_gmat", "class_avg_gmat") and gmat_known:
            continue
        if f.program_id == pid and f.status != "verified" and (f.field, f.source_type) not in have:
            gaps.append({"field": f.field, "label": FIELD_LABEL[f.field], "reason": GAP_REASON[f.status], "source_url": f.source_url or None,
                         "publisher": f.publisher, "status": f.status})
    return {"facts": facts, "gaps": gaps}


def _pick(pid: str, field: str, source_type: str | None = None) -> SuppFact | None:
    return next((f for f in verified(pid) if f.field == field and (source_type is None or f.source_type == source_type)), None)


def cost_summary(pid: str, core_coa: dict | None = None, core_tuition: dict | None = None) -> dict:
    """Separate, labeled cost lines for one program. Values are never summed or converted across sources."""
    lines = []

    def add(kind: str, label_: str, value, period, basis, f: SuppFact | None = None, url: str | None = None, publisher: str | None = None):
        lines.append({"kind": kind, "label": label_, "value": value, "period": period, "period_basis": basis,
                      "source_url": url or (f.source_url if f else None), "publisher": publisher or (f.publisher if f else None),
                      "notes": f.notes if f else ""})
    off_coa = _pick(pid, "cost_of_attendance", "official")
    if core_coa:
        add("official", "Cost of attendance", core_coa["value"], core_coa.get("period"), "annual", url=core_coa.get("source_url"), publisher="Official school page")
    elif off_coa:
        add("official", "Cost of attendance", off_coa.value, off_coa.period, off_coa.period_basis, off_coa)
    if core_tuition:
        add("official", "Tuition", core_tuition["value"], core_tuition.get("period"), "annual", url=core_tuition.get("source_url"), publisher="Official school page")
    fee = _pick(pid, "mandatory_fees", "official") or _pick(pid, "mandatory_fees", "secondary")
    if fee:
        add("official" if fee.source_type == "official" else "reported", "Mandatory fees", fee.value, fee.period, fee.period_basis, fee)
    if not core_tuition:
        t = _pick(pid, "tuition", "secondary") or _pick(pid, "tuition_and_fees", "secondary")
        if t:
            add("reported", FIELD_LABEL[t.field], t.value, t.period, t.period_basis, t)
    est = _pick(pid, "est_annual_cost")
    if est:
        add("estimate", "Estimated one-year cost", est.value, est.period, "annual", est)
    est2 = _pick(pid, "est_two_year_cost")
    if est2:
        add("estimate", "Estimated two-year cost", est2.value, est2.period, "full_program", est2)
    ca = _pick(pid, "reported_cost_of_attendance")
    if ca:
        add("reported", "Cost of attendance as compiled", ca.value, ca.period, "annual", ca)
    est_line = next((x for x in lines if x["label"] == "Estimated one-year cost"), None)
    # An estimate that may use the in-state/resident rate is misleading for international applicants as a headline or a
    # budget comparison; it stays in `lines` with its caveat but is not promoted.
    if est_line and re.search(r"in-state|resident", est_line["notes"] or "", re.I):
        est_line = None
    return {"lines": lines,
            "official_coa": next((x for x in lines if x["kind"] == "official" and x["label"] == "Cost of attendance"), None),
            "estimate_annual": est_line}
