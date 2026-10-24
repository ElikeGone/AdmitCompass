"""Applicant profile. Deliberately excludes names, contact details, IDs, birthdates, and exact addresses.

Every field except profile_id is optional so missing information stays explicitly unknown.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..core.safety import injection_hits, pii_hits


class TestStatus(str, Enum):
    NOT_STARTED = "not_started"
    PREPARING = "preparing"
    GMAT_TAKEN = "gmat_taken"
    GMAT_FOCUS_TAKEN = "gmat_focus_taken"
    GRE_TAKEN = "gre_taken"
    EA_TAKEN = "ea_taken"
    UNKNOWN = "unknown"


class Education(BaseModel):
    model_config = ConfigDict(extra="forbid")
    degree_level: str = Field(description="e.g. Bachelor's, Master's")
    field: str
    country: str | None = None
    gpa_band: str | None = Field(default=None, description="Coarse band only, e.g. 'top 10% of class', '3.5-3.7'")


class ApplicantProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")  # rejects unexpected (possibly sensitive) fields

    profile_id: str = Field(pattern=r"^[a-z0-9-]+$")
    is_fictional: bool = Field(description="Fixtures must be fictional; real users are session-only")
    citizenship_country: str | None = Field(default=None, description="Country only; no passport/visa numbers")
    needs_us_work_authorization: bool | None = None
    education: list[Education] = Field(default_factory=list)
    years_work_experience: float | None = Field(default=None, ge=0, le=40)
    current_industry: str | None = None
    current_function: str | None = None
    target_function: str | None = None
    target_industry: str | None = None
    target_roles: list[str] = Field(default_factory=list)
    preferred_us_states: list[str] = Field(default_factory=list, description="Two-letter codes; empty = no preference")
    long_term_location: str | None = Field(default=None, description="e.g. 'US', 'home country', 'flexible'")
    budget_usd: float | None = Field(default=None, gt=0, description="Budget amount as entered")
    budget_period: Literal["per_academic_year", "total_program"] | None = None
    max_total_budget_usd_per_year: float | None = Field(
        default=None, gt=0,
        description="Per-academic-year budget used for affordability. Set only when the period is per year; "
                    "a whole-program budget is never silently converted.")
    funding_notes: str | None = None
    quantitative_background: str | None = None
    test_status: TestStatus = TestStatus.UNKNOWN
    test_score: int | None = Field(default=None, ge=0, le=900)
    target_intake_year: int | None = Field(default=None, ge=2026, le=2032)
    weeks_until_first_application: int | None = Field(default=None, ge=0, le=104)
    hours_per_week_available: int | None = Field(default=None, ge=0, le=80)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def reconcile_budget_and_screen_text(self) -> "ApplicantProfile":
        # Budget: keep the period explicit. Legacy profiles only set max_total_budget_usd_per_year (per year).
        if self.budget_usd is None and self.max_total_budget_usd_per_year is not None:
            self.budget_usd, self.budget_period = self.max_total_budget_usd_per_year, "per_academic_year"
        if self.budget_usd is not None and self.budget_period is None:
            raise ValueError("budget_period is required when budget_usd is given")
        if self.budget_period == "per_academic_year":
            self.max_total_budget_usd_per_year = self.budget_usd
        elif self.budget_period == "total_program":
            self.max_total_budget_usd_per_year = None  # not comparable with one-year published costs
        # Free text: block prompt-injection instructions and sensitive identifiers.
        for path, text in _strings(self.model_dump(exclude={"profile_id"})):
            if injection_hits(text):
                raise ValueError(f"{path} looks like instructions to the AI, not profile information. Please rephrase.")
            found = pii_hits(text)
            if found:
                raise ValueError(f"{path} appears to contain a {found[0]}. AdmitCompass does not need personal identifiers.")
        return self

    def known_fields(self) -> dict:
        return self.model_dump(exclude_none=True, mode="json")


def _strings(obj, path=""):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _strings(v, f"{path}[{i}]")
