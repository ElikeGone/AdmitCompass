"""Validated outputs for each agent, the trace, and the final RecommendationReport."""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .claims import Claim

AgentName = Literal["pathway_matcher", "evidence_analyst", "strategy_planner", "skeptic"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ---------- Pathway Matcher ----------
class TargetRole(_Strict):
    title: str
    rationale: str


class Candidate(_Strict):
    program_id: str
    career_fit: Literal["strong", "moderate", "weak"]
    fit_rationale: str
    tradeoffs: list[str] = Field(default_factory=list)


class Exclusion(_Strict):
    program_id: str
    reason: str


class PathwayOutput(_Strict):
    target_roles: list[TargetRole] = Field(min_length=1, max_length=4)
    candidates: list[Candidate] = Field(min_length=1, max_length=5)
    excluded: list[Exclusion] = Field(default_factory=list)
    missing_profile_info: list[str] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)


# ---------- Evidence Analyst ----------
class Dossier(_Strict):
    program_id: str
    claims: list[Claim] = Field(min_length=1)
    affordability: Literal["within_budget", "over_budget", "unknown"]
    affordability_basis: str
    stem_status: Literal["verified_designated", "verified_not_designated", "unknown"]
    sponsorship_status: Literal["unknown", "employer_specific_evidence"]
    source_strength: str = Field(description="Summary of verification levels and freshness")
    flags: list[str] = Field(default_factory=list)


class MetricComparison(_Strict):
    program_ids: list[str] = Field(min_length=2)
    metric: Literal["employment_rate", "median_base_salary"]
    treated_as_comparable: bool
    reason: str


class EvidenceOutput(_Strict):
    dossiers: list[Dossier] = Field(min_length=1)
    metric_comparisons: list[MetricComparison] = Field(default_factory=list)
    unsupported_claims_flagged: list[str] = Field(default_factory=list)


# ---------- Strategy Planner ----------
class TestGuidance(_Strict):
    recommendation: Literal["take_gmat", "take_gre", "either_gmat_or_gre", "use_existing_score", "retake_existing_test", "undecided_need_info"]
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)


class Gap(_Strict):
    gap: str
    severity: Literal["high", "medium", "low"]
    action: str


class WeekPlan(_Strict):
    week: int = Field(ge=1, le=52)
    priority: Literal["high", "medium", "low"]
    actions: list[str] = Field(min_length=1, max_length=5)


class RoadmapPhase(_Strict):
    phase: str
    timing: str = Field(description="Relative timing only, e.g. 'Weeks 1-4' — no invented calendar deadlines")
    milestones: list[str] = Field(min_length=1)
    human_checkpoint: bool = Field(description="True where the applicant must decide or verify personally")


class StrategyOutput(_Strict):
    test_guidance: TestGuidance
    gaps: list[Gap] = Field(min_length=1)
    weekly_plan: list[WeekPlan] = Field(min_length=1, max_length=16)
    roadmap: list[RoadmapPhase] = Field(min_length=2)
    claims: list[Claim] = Field(default_factory=list)


# ---------- Skeptic ----------
class SkepticFinding(_Strict):
    target_agent: Literal["pathway_matcher", "evidence_analyst", "strategy_planner"]
    target_ref: str = Field(description="program_id, claim text, or plan item challenged")
    category: Literal["unsupported_claim", "affordability", "weak_source", "incomparable_metrics",
                      "immigration_sponsorship", "overconfidence", "missing_info", "other"]
    severity: Literal["high", "medium", "low"]
    issue: str
    required_fix: str


class RevisionRequest(_Strict):
    target_agent: Literal["pathway_matcher", "evidence_analyst", "strategy_planner"]
    instructions: str


class SkepticOutput(_Strict):
    findings: list[SkepticFinding] = Field(default_factory=list)
    revision_request: RevisionRequest | None = None
    overall_assessment: str


# ---------- Trace / report ----------
class TraceEvent(BaseModel):
    seq: int
    kind: Literal["agent_start", "llm_call", "tool_call", "validation", "grounding", "handoff",
                  "revision", "budget_stop", "agent_failure", "run_end"]
    agent: str
    detail: dict[str, Any] = Field(default_factory=dict)


class GroundingViolation(BaseModel):
    agent: str
    rule: str
    detail: str
    action: str = Field(description="What the orchestrator did: rejected, dropped, corrected, retried")


class ProgramFactView(BaseModel):
    """Deterministic facts copied from the evidence store — never from model text."""
    fact: str
    status: str
    value: Any = None
    period: str | None = None
    definition: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    verification_level: str | None = None
    freshness_warning: str | None = None
    note: str = ""


class ProgramRecommendation(BaseModel):
    program_id: str
    program_name: str
    career_fit: str
    fit_rationale: str
    tradeoffs: list[str]
    affordability: str
    affordability_basis: str
    stem_status: str
    sponsorship_status: str
    facts: list[ProgramFactView]
    analyst_claims: list[Claim]
    flags: list[str]


class AgentUsage(BaseModel):
    agent: str
    calls: int
    input_tokens: int | None
    cached_input_tokens: int | None
    output_tokens: int | None
    reasoning_tokens: int | None = None
    elapsed_seconds: float
    estimated_cost_usd: float | None


class RecommendationReport(BaseModel):
    run_id: str
    profile_id: str
    status: Literal["completed", "completed_with_violations", "stopped_budget", "failed_closed"]
    model: str
    target_roles: list[TargetRole] = Field(default_factory=list)
    recommendations: list[ProgramRecommendation] = Field(default_factory=list)
    excluded_programs: list[Exclusion] = Field(default_factory=list)
    metric_comparability: list[dict] = Field(default_factory=list)
    strategy: StrategyOutput | None = None
    skeptic: SkepticOutput | None = None
    revision_performed: bool = False
    revision_target: str | None = None
    grounding_violations: list[GroundingViolation] = Field(default_factory=list)
    usage_by_agent: list[AgentUsage] = Field(default_factory=list)
    totals: dict[str, Any] = Field(default_factory=dict)
    disclaimers: list[str] = Field(default_factory=list)
    error: str | None = None
