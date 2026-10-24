"""Supplementary evidence: official extras (fees, class profile, scholarships, deadlines) and secondary-source figures
(Poets&Quants estimates, Clear Admit compiled costs). Kept separate from the core evidence store so a secondary value can
never overwrite an official one; both are shown side by side with distinct labels."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..core.safety import injection_hits

SuppField = Literal["tuition", "mandatory_fees", "tuition_and_fees", "cost_of_attendance", "reported_cost_of_attendance",
                    "est_annual_cost", "est_two_year_cost", "class_size", "class_median_gmat", "class_avg_gmat",
                    "class_pct_international", "scholarships", "application_deadlines", "hiring_employers", "ranking"]
FIELD_LABEL = {
    "tuition": "Tuition", "mandatory_fees": "Mandatory fees", "tuition_and_fees": "Tuition and fees",
    "cost_of_attendance": "Cost of attendance", "reported_cost_of_attendance": "Cost of attendance (as compiled)",
    "est_annual_cost": "Estimated one-year cost", "est_two_year_cost": "Estimated two-year cost", "class_size": "Class size",
    "class_median_gmat": "Median GMAT", "class_avg_gmat": "Average GMAT", "class_pct_international": "International students",
    "scholarships": "Scholarships and fellowships", "application_deadlines": "Application deadlines",
    "hiring_employers": "Employers that hired graduates", "ranking": "Composite ranking (context only)",
}


class SuppFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fact_id: str = Field(pattern=r"^sx-[a-z0-9-]+$")
    program_id: str = Field(pattern=r"^[a-z0-9-]+$")
    field: SuppField
    value: Any = None
    unit: Literal["USD", "students", "score", "percent", "text", "dates", "rank"]
    period: str | None = None                    # "2026-2027", "Class of 2027"
    period_basis: Literal["annual", "full_program", "semester", "cohort", "cycle"]
    source_url: str = Field(default="", pattern=r"^(https://.*)?$")   # may be empty only for not_found research gaps
    publisher: str
    source_type: Literal["official", "secondary"]
    value_kind: Literal["published", "reported", "estimate"]   # reported = school figure republished by a third party
    retrieved_on: str
    status: Literal["verified", "unverified", "blocked", "not_found"]
    validation: str = ""                         # what the validator checked
    excerpt: str = ""
    notes: str = ""

    @model_validator(mode="after")
    def rules(self) -> "SuppFact":
        if self.status == "verified" and self.value is None:
            raise ValueError("verified facts need a value")
        if self.status in ("verified", "unverified") and not self.source_url:
            raise ValueError("checked facts need an https source_url")
        if self.source_type == "secondary" and self.field == "cost_of_attendance":
            raise ValueError("secondary sources can't supply an official cost_of_attendance; use reported_cost_of_attendance")
        if self.value_kind == "estimate" and self.source_type == "official":
            raise ValueError("official published values are not estimates")
        if injection_hits(self.excerpt) or injection_hits(self.notes) or injection_hits(" | ".join(map(str, self.value)) if isinstance(self.value, list) else str(self.value or "")):
            raise ValueError("excerpt contains instruction-like text")
        return self
