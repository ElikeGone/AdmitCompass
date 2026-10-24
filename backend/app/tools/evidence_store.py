"""Deterministic evidence retrieval. All program facts used by agents must come through here.

No model calls. Data comes only from data/programs/programs.json and data/sources/source_registry.json.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..schemas.claims import Claim, ClaimLabel
from ..schemas.programs import (
    FactStatus, ProgramDataset, ProgramRecord, Source, SourceType,
    parse_academic_year, parse_class_year,
)

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
SOURCE_LABELS = {
    SourceType.OFFICIAL_UNIVERSITY: "Official university source",
    SourceType.GOVERNMENT: "Official government source",
    SourceType.THIRD_PARTY: "Third-party source (not official)",
}


class EvidenceNotFoundError(KeyError):
    pass


def stale_after_months() -> int:
    return int(os.getenv("ADMITCOMPASS_SOURCE_STALE_MONTHS", "18"))


def data_reference_date(period: str | None) -> date | None:
    """Approximate date the data describes: end of academic year, or end of the graduating year."""
    ay = parse_academic_year(period)
    if ay:
        return date(ay[1], 6, 30)
    cy = parse_class_year(period)
    if cy:
        return date(cy, 12, 31)
    return None


def freshness(period: str | None, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    ref = data_reference_date(period)
    if ref is None:
        return {"data_period": period, "data_year": None, "age_months": None, "stale": None,
                "warning": "Data period not stated by source; freshness unknown."}
    age = max(0, (today.year - ref.year) * 12 + (today.month - ref.month))
    stale = age > stale_after_months()
    return {"data_period": period, "data_year": ref.year, "age_months": age, "stale": stale,
            "warning": f"Data is from {period} (~{age} months old); check for a newer release." if stale else None}


def verification_level(ev) -> str:
    """rechecked_first_hand > source_backed_excerpt > source_backed_paraphrase."""
    if ev.rechecked:
        return "rechecked_first_hand"
    return "source_backed_paraphrase" if ev.excerpt_is_paraphrase else "source_backed_excerpt"


@dataclass(frozen=True)
class FactWithEvidence:
    program_id: str
    fact_name: str
    status: str
    value: Any
    unit: str
    period: str | None
    definition: str | None
    note: str
    evidence: list[dict]
    freshness: dict

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class EvidenceStore:
    def __init__(self, dataset: ProgramDataset):
        self.dataset = dataset
        self._programs = {p.program_id: p for p in dataset.programs}
        self._sources = {s.source_id: s for s in dataset.sources}
        self._evidence = {e.evidence_id: (p.program_id, e) for p in dataset.programs for e in p.evidence}

    @classmethod
    def load(cls, data_dir: Path = DATA_DIR) -> "EvidenceStore":
        programs = json.loads((data_dir / "programs" / "programs.json").read_text(encoding="utf-8"))
        sources = json.loads((data_dir / "sources" / "source_registry.json").read_text(encoding="utf-8"))
        return cls(ProgramDataset(schema_version=programs["schema_version"],
                                  programs=programs["programs"], sources=sources["sources"]))

    # --- listing / retrieval ---
    def list_programs(self) -> list[dict]:
        return [{"program_id": p.program_id, "university": p.university, "school": p.school,
                 "program_name": p.program_name, "degree": p.degree} for p in self.dataset.programs]

    def get_program(self, program_id: str) -> ProgramRecord:
        try:
            return self._programs[program_id]
        except KeyError:
            raise EvidenceNotFoundError(f"unknown program_id {program_id!r}") from None

    def get_source(self, source_id: str) -> Source:
        return self._sources[source_id]

    def get_evidence(self, evidence_id: str) -> dict:
        if evidence_id not in self._evidence:
            raise EvidenceNotFoundError(f"unknown evidence_id {evidence_id!r}")
        program_id, ev = self._evidence[evidence_id]
        src = self._sources[ev.source_id]
        return {"evidence_id": ev.evidence_id, "program_id": program_id, "excerpt": ev.excerpt,
                "excerpt_is_paraphrase": ev.excerpt_is_paraphrase, "rechecked": ev.rechecked,
                "verification_level": verification_level(ev), "source_id": src.source_id,
                "source_url": str(src.url), "source_title": src.title, "publisher": src.publisher,
                "source_type": src.source_type.value, "source_label": SOURCE_LABELS[src.source_type],
                "accessed": src.accessed, "checked_on": src.checked_on.isoformat() if src.checked_on else None}

    def fact_for_evidence(self, evidence_id: str) -> tuple[str, str]:
        """Map an evidence id to (program_id, fact_name) it supports."""
        if evidence_id not in self._evidence:
            raise EvidenceNotFoundError(f"unknown evidence_id {evidence_id!r}")
        pid = self._evidence[evidence_id][0]
        for name, f in self._programs[pid].facts.items():
            if evidence_id in f.evidence_ids:
                return pid, name
        raise EvidenceNotFoundError(f"evidence_id {evidence_id!r} supports no fact")

    def get_fact(self, program_id: str, fact_name: str) -> FactWithEvidence:
        prog = self.get_program(program_id)
        if fact_name not in prog.facts:
            raise EvidenceNotFoundError(f"unknown fact {fact_name!r}")
        f = prog.facts[fact_name]
        return FactWithEvidence(
            program_id=program_id, fact_name=fact_name, status=f.status.value, value=f.value,
            unit=f.unit.value, period=f.period, definition=f.definition, note=f.note,
            evidence=[self.get_evidence(i) for i in f.evidence_ids],
            freshness=freshness(f.period) if f.status is FactStatus.VERIFIED else freshness(None) | {"warning": None},
        )

    # --- filtering (only verified facts count; unknowns never pass a positive filter) ---
    def filter_programs(self, *, stem_designated: bool | None = None, max_cost_of_attendance: float | None = None,
                        max_tuition: float | None = None, states: list[str] | None = None,
                        max_duration_months: float | None = None, include_unknown: bool = False) -> list[str]:
        out = []
        for p in self.dataset.programs:
            checks = []
            if stem_designated is not None:
                f = p.facts["stem_designation"]
                checks.append(None if f.status is FactStatus.UNKNOWN else f.value["designated"] == stem_designated)
            for name, limit in (("cost_of_attendance", max_cost_of_attendance), ("tuition", max_tuition),
                                ("duration_months", max_duration_months)):
                if limit is not None:
                    f = p.facts[name]
                    checks.append(None if f.status is FactStatus.UNKNOWN else f.value <= limit)
            if states:
                f = p.facts["location"]
                checks.append(None if f.status is FactStatus.UNKNOWN else f.value["state"] in states)
            if all(c is True or (c is None and include_unknown) for c in checks):
                out.append(p.program_id)
        return out

    # --- claim support ---
    def evidence_for_claim(self, claim: Claim) -> list[dict]:
        """Return evidence for a claim; raises if any evidence id does not exist."""
        return [self.get_evidence(i) for i in claim.evidence_ids]

    def validate_claim(self, claim: Claim) -> None:
        """Reject verified claims unless every evidence id exists and points to an accessed source."""
        evs = self.evidence_for_claim(claim)
        if claim.label is ClaimLabel.VERIFIED_FACT:
            if not evs and not claim.evidence:
                raise ValueError("verified_fact claim has no evidence")
            if any(not e["accessed"] for e in evs):
                raise ValueError("verified_fact claim cites a source that was not accessed")


@lru_cache(maxsize=1)
def default_store() -> EvidenceStore:
    return EvidenceStore.load()
