"""Discovered programs: a separate, weaker tier than the verified evidence store.

A discovered program records only that a real program exists, from where we learned it, and where it is.
It deliberately has NO fields for tuition, cost, employment, STEM, admissions odds, or sponsorship
(extra fields are forbidden), and its status can never be "verified". Promotion to the verified evidence
store requires the full per-fact evidence process (see docs/decisions.md ADR-014).
"""
from __future__ import annotations

from datetime import date
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from ..core.safety import injection_hits

DiscoveryStatus = Literal["needs_verification", "not_confirmed"]


class DiscoveredProgram(BaseModel):
    model_config = ConfigDict(extra="forbid")

    discovery_id: str = Field(pattern=r"^disc-[a-z0-9-]+$")
    university: str = Field(min_length=2)
    school: str | None = None
    program_name: str = Field(min_length=2)
    degree_type: Literal["MBA"]
    format: str = Field(description="As stated by the source, e.g. 'full-time'")
    city: str | None = None
    state: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    location_basis: str = Field(description="How the location is known, or why it is missing")
    provenance_url: HttpUrl
    page_title: str | None = None
    excerpt: str | None = Field(default=None, max_length=400)
    discovered_on: date
    fetched: bool = Field(description="True only if the provenance page was actually retrieved")
    verification_status: DiscoveryStatus
    notes: str = ""

    @field_validator("provenance_url")
    @classmethod
    def https_only(cls, v: HttpUrl) -> HttpUrl:
        if v.scheme != "https":
            raise ValueError("provenance_url must be https")
        return v

    @field_validator("excerpt", "page_title", "notes")
    @classmethod
    def no_instructions(cls, v):
        if v and injection_hits(v):
            raise ValueError("instruction-like text in discovered record; rejected")
        return v

    @model_validator(mode="after")
    def status_matches_retrieval(self) -> "DiscoveredProgram":
        if self.fetched and not self.excerpt:
            raise ValueError("a fetched record needs an excerpt from the page")
        if not self.fetched and self.verification_status != "not_confirmed":
            raise ValueError("records whose page was not retrieved must be 'not_confirmed'")
        if self.discovered_on > date.today():
            raise ValueError("discovered_on is in the future")
        return self

    @property
    def domain(self) -> str:
        return registrable_domain(str(self.provenance_url))


class DiscoveryIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str
    built_on: date
    method: str
    is_live_search: Literal[False] = False
    sources_note: str
    programs: list[DiscoveredProgram]

    @model_validator(mode="after")
    def unique_ids(self) -> "DiscoveryIndex":
        ids = [p.discovery_id for p in self.programs]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate discovery_id")
        return self


def registrable_domain(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host
