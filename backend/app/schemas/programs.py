"""Program dataset schemas: source registry, evidence items, and per-field facts.

Every program fact is either `verified` (value + at least one evidence id that points to an
accessed source) or `unknown` (value is None). Nothing in between.
"""
from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from ..core.safety import injection_hits

ACADEMIC_YEAR_RE = re.compile(r"^(\d{4})-(\d{4})$")
CLASS_YEAR_RE = re.compile(r"^Class of (\d{4})$")

FACT_NAMES = (
    "location", "duration_months", "application_requirements", "test_policy",
    "tuition", "cost_of_attendance", "stem_designation",
    "employment_rate", "median_base_salary", "industry_breakdown", "function_breakdown",
    "international_employment", "sponsorship", "application_deadlines",
)
FactName = Literal[
    "location", "duration_months", "application_requirements", "test_policy",
    "tuition", "cost_of_attendance", "stem_designation",
    "employment_rate", "median_base_salary", "industry_breakdown", "function_breakdown",
    "international_employment", "sponsorship", "application_deadlines",
]
COST_FACTS = {"tuition", "cost_of_attendance"}
OUTCOME_FACTS = {"employment_rate", "median_base_salary", "industry_breakdown", "function_breakdown"}


class SourceType(str, Enum):
    OFFICIAL_UNIVERSITY = "official_university"
    GOVERNMENT = "government"
    THIRD_PARTY = "third_party"


class Unit(str, Enum):
    USD = "USD"
    PERCENT = "percent"
    MONTHS = "months"
    TEXT = "text"
    TEXT_LIST = "text_list"
    PERCENT_MAP = "percent_map"
    LOCATION = "location"
    STEM = "stem"
    SPONSORSHIP = "sponsorship"


class FactStatus(str, Enum):
    VERIFIED = "verified"
    UNKNOWN = "unknown"


class Source(BaseModel):
    source_id: str = Field(pattern=r"^src-[a-z0-9-]+$")
    url: HttpUrl
    title: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    source_type: SourceType
    accessed: bool = Field(description="True only if the page was actually fetched during collection")
    checked_on: date | None = None
    note: str = ""

    @field_validator("title", "note")
    @classmethod
    def no_embedded_instructions(cls, v: str) -> str:
        if injection_hits(v):
            raise ValueError("source text contains instruction-like text (possible prompt injection); rejected")
        return v

    @model_validator(mode="after")
    def accessed_needs_date(self) -> "Source":
        if self.accessed and self.checked_on is None:
            raise ValueError(f"{self.source_id}: accessed sources need checked_on")
        if self.checked_on and self.checked_on > date.today():
            raise ValueError(f"{self.source_id}: checked_on is in the future")
        return self


class EvidenceItem(BaseModel):
    evidence_id: str = Field(pattern=r"^ev-[a-z0-9-]+$")
    source_id: str
    excerpt: str = Field(min_length=1, max_length=600)
    excerpt_is_paraphrase: bool = False
    rechecked: bool = Field(default=False, description="Independently re-fetched and matched by a second check")

    @field_validator("excerpt")
    @classmethod
    def no_embedded_instructions(cls, v: str) -> str:
        if injection_hits(v):
            raise ValueError("evidence excerpt contains instruction-like text (possible prompt injection); rejected")
        return v


class StemValue(BaseModel):
    designated: bool
    scope: str = Field(min_length=1, description="Exactly which degree/track the source covers")
    cip_code: str | None = Field(default=None, pattern=r"^\d{2}\.\d{4}$")


class SponsorshipValue(BaseModel):
    """Only employer-specific, source-stated sponsorship facts are allowed."""
    employer: str = Field(min_length=1)
    statement: str = Field(min_length=1)


class LocationValue(BaseModel):
    city: str
    state: str = Field(pattern=r"^[A-Z]{2}$")


class Fact(BaseModel):
    status: FactStatus
    value: Any = None
    unit: Unit
    period: str | None = Field(default=None, description="Academic year 'YYYY-YYYY' or 'Class of YYYY'")
    definition: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    note: str = ""
    checked: bool = Field(default=True, description="Unknown facts: True = official pages were checked and it isn't stated; "
                                                     "False = not checked yet")

    @model_validator(mode="after")
    def check_status_and_units(self) -> "Fact":
        if self.status is FactStatus.UNKNOWN:
            if self.value is not None:
                raise ValueError("unknown facts must have value=None")
            return self
        if not self.checked:
            raise ValueError("a verified fact is by definition checked")
        if self.value is None or not self.evidence_ids:
            raise ValueError("verified facts need a value and at least one evidence_id")
        v, u = self.value, self.unit
        if u is Unit.USD and not (isinstance(v, (int, float)) and v > 0):
            raise ValueError("USD values must be positive numbers")
        if u is Unit.PERCENT and not (isinstance(v, (int, float)) and 0 <= v <= 100):
            raise ValueError("percent values must be 0–100")
        if u is Unit.MONTHS and not (isinstance(v, (int, float)) and 0 < v <= 60):
            raise ValueError("months must be 1–60")
        if u is Unit.PERCENT_MAP:
            if not isinstance(v, dict) or not v or not all(isinstance(x, (int, float)) and 0 <= x <= 100 for x in v.values()):
                raise ValueError("percent_map must be a non-empty {label: 0–100} dict")
        if u is Unit.TEXT_LIST and not (isinstance(v, list) and v and all(isinstance(x, str) for x in v)):
            raise ValueError("text_list must be a non-empty list of strings")
        if u is Unit.TEXT and not (isinstance(v, (str, int, float)) and str(v).strip()):
            raise ValueError("text must be non-empty")
        if u is Unit.STEM:
            self.value = StemValue.model_validate(v).model_dump()
        if u is Unit.SPONSORSHIP:
            self.value = SponsorshipValue.model_validate(v).model_dump()
        if u is Unit.LOCATION:
            self.value = LocationValue.model_validate(v).model_dump()
        return self


def parse_academic_year(period: str | None) -> tuple[int, int] | None:
    m = ACADEMIC_YEAR_RE.match(period or "")
    if not m:
        return None
    start, end = int(m.group(1)), int(m.group(2))
    return (start, end) if end == start + 1 else None


def parse_class_year(period: str | None) -> int | None:
    m = CLASS_YEAR_RE.match(period or "")
    return int(m.group(1)) if m else None


class ProgramRecord(BaseModel):
    program_id: str = Field(pattern=r"^[a-z0-9-]+$")
    university: str
    school: str
    program_name: str
    degree: Literal["MBA"]
    collection_tier: Literal["curated", "enriched"] = "curated"
    facts: dict[FactName, Fact]
    evidence: list[EvidenceItem] = Field(default_factory=list)

    @field_validator("facts")
    @classmethod
    def all_fields_present(cls, facts: dict) -> dict:
        missing = set(FACT_NAMES) - set(facts)
        if missing:
            raise ValueError(f"missing fact fields (use status=unknown instead): {sorted(missing)}")
        return facts

    @model_validator(mode="after")
    def check_links_and_periods(self) -> "ProgramRecord":
        ev_ids = [e.evidence_id for e in self.evidence]
        if len(ev_ids) != len(set(ev_ids)):
            raise ValueError(f"{self.program_id}: duplicate evidence ids")
        known = set(ev_ids)
        for name, fact in self.facts.items():
            bad = [i for i in fact.evidence_ids if i not in known]
            if bad:
                raise ValueError(f"{self.program_id}.{name}: unknown evidence ids {bad}")
            if fact.status is not FactStatus.VERIFIED:
                continue
            if name in COST_FACTS and (fact.unit is not Unit.USD or parse_academic_year(fact.period) is None):
                raise ValueError(f"{self.program_id}.{name}: costs need unit USD and period 'YYYY-YYYY' (consecutive years)")
            if name in OUTCOME_FACTS and (parse_class_year(fact.period) is None or not fact.definition):
                raise ValueError(f"{self.program_id}.{name}: outcomes need period 'Class of YYYY' and a metric definition")
            if name == "stem_designation" and fact.unit is not Unit.STEM:
                raise ValueError(f"{self.program_id}.stem_designation must use unit 'stem'")
            if name == "sponsorship" and fact.unit is not Unit.SPONSORSHIP:
                raise ValueError(f"{self.program_id}.sponsorship must be employer-specific (unit 'sponsorship')")
        return self


class ProgramDataset(BaseModel):
    schema_version: str
    programs: list[ProgramRecord]
    sources: list[Source]

    @model_validator(mode="after")
    def check_cross_links(self) -> "ProgramDataset":
        src = {s.source_id: s for s in self.sources}
        if len(src) != len(self.sources):
            raise ValueError("duplicate source ids")
        pids = [p.program_id for p in self.programs]
        if len(pids) != len(set(pids)):
            raise ValueError("duplicate program ids")
        all_ev: set[str] = set()
        for p in self.programs:
            for e in p.evidence:
                if e.evidence_id in all_ev:
                    raise ValueError(f"evidence id {e.evidence_id} reused across programs")
                all_ev.add(e.evidence_id)
                s = src.get(e.source_id)
                if s is None:
                    raise ValueError(f"{e.evidence_id}: unknown source_id {e.source_id}")
                if not s.accessed:
                    raise ValueError(f"{e.evidence_id}: cites {s.source_id}, which was not accessed")
        return self
