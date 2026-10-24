"""Evidence and Claim schemas. Every claim carries an epistemic label."""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, model_validator


class ClaimLabel(str, Enum):
    VERIFIED_FACT = "verified_fact"
    INFERENCE = "inference"
    UNKNOWN = "unknown"
    ADVICE = "advice"


class Evidence(BaseModel):
    source_url: HttpUrl
    source_title: str = Field(min_length=1)
    verified_on: date
    excerpt: str = Field(min_length=1, max_length=1000, description="Quoted or summarized supporting text")

    @model_validator(mode="after")
    def not_in_future(self) -> "Evidence":
        if self.verified_on > date.today():
            raise ValueError("verified_on cannot be in the future")
        return self


class Claim(BaseModel):
    text: str = Field(min_length=1)
    label: ClaimLabel
    evidence: list[Evidence] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list, description="Ids from the evidence store (ev-...)")
    based_on: list[str] = Field(default_factory=list, description="Ids/texts of claims an inference or advice relies on")

    @model_validator(mode="after")
    def verified_requires_evidence(self) -> "Claim":
        # Existence of evidence_ids is checked against the store by EvidenceStore.validate_claim.
        if self.label is ClaimLabel.VERIFIED_FACT and not (self.evidence or self.evidence_ids):
            raise ValueError("verified_fact claims require Evidence (source_url + verified_on) or evidence_ids")
        return self
