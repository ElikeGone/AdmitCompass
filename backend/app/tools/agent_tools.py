"""Deterministic tools exposed to agents via function calling. Every call is logged with the requesting agent.

Tools only READ the evidence store. Nothing a model writes can create or change a program fact.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from ..core.budget import RunBudget
from ..core.safety import UNTRUSTED_NOTE
from ..schemas.programs import FACT_NAMES, FactStatus
from .evidence_store import EvidenceNotFoundError, EvidenceStore

OVERVIEW_FACTS = ("location", "tuition", "cost_of_attendance", "stem_designation", "employment_rate",
                  "median_base_salary", "test_policy")


def _norm_def(d: str | None) -> str:
    return " ".join((d or "").lower().split())


def compare_metrics(store: EvidenceStore, program_ids: list[str], metric: str) -> dict:
    """Deterministic comparability: same cohort year AND same metric definition text."""
    rows, unknown = [], []
    for pid in program_ids:
        f = store.get_fact(pid, metric)
        if f.status != "verified":
            unknown.append(pid)
            continue
        rows.append({"program_id": pid, "value": f.value, "period": f.period, "definition": f.definition,
                     "evidence_ids": [e["evidence_id"] for e in f.evidence]})
    groups: dict[tuple, list[str]] = {}
    for r in rows:
        groups.setdefault((r["period"], _norm_def(r["definition"])), []).append(r["program_id"])
    comparable_sets = [ids for ids in groups.values() if len(ids) > 1]
    return {"metric": metric, "rows": rows, "unknown_programs": unknown,
            "comparable_groups": comparable_sets,
            "all_comparable": len(rows) > 1 and len(groups) == 1,
            "rule": "Comparable only if cohort period and metric definition are identical."}


class ToolBox:
    """Holds the store, budget, and trace callback; builds per-agent tool specs."""

    def __init__(self, store: EvidenceStore, budget: RunBudget, log: Callable[[str, str, dict], None]):
        self.store, self.budget, self.log = store, budget, log
        self._cache: dict[tuple[str, str], str] = {}  # identical repeat calls return the cached result
        self.by_agent: dict[str, list[dict]] = {}     # successful results per agent (reused by repair-mode retries)
        self._impl: dict[str, Callable[..., Any]] = {
            "search_programs": self.search_programs,
            "get_program_overview": self.get_program_overview,
            "get_program_facts": self.get_program_facts,
            "get_evidence": self.get_evidence,
            "compare_employment_metrics": self.compare_employment_metrics,
            "get_sponsorship_evidence": self.get_sponsorship_evidence,
        }

    # ----- tool implementations -----
    def search_programs(self, stem_designated: bool | None = None, max_cost_of_attendance: float | None = None,
                        states: list[str] | None = None) -> dict:
        matches = self.store.filter_programs(stem_designated=stem_designated,
                                             max_cost_of_attendance=max_cost_of_attendance, states=states)
        with_unknown = self.store.filter_programs(stem_designated=stem_designated,
                                                  max_cost_of_attendance=max_cost_of_attendance, states=states,
                                                  include_unknown=True)
        return {"matching_verified": matches,
                "unverified_could_match": [p for p in with_unknown if p not in matches],
                "all_programs": self.store.list_programs()}

    def _fact_view(self, pid: str, name: str) -> dict:
        f = self.store.get_fact(pid, name)
        out = {"status": f.status}
        if f.status == "verified":
            out.update(value=f.value, period=f.period, definition=f.definition,
                       evidence_ids=[e["evidence_id"] for e in f.evidence],
                       verification_level=[e["verification_level"] for e in f.evidence],
                       freshness_warning=f.freshness.get("warning"))
        if f.note:
            out["note"] = f.note[:300]
        return out

    def get_program_overview(self, program_id: str) -> dict:
        p = self.store.get_program(program_id)
        return {"program_id": program_id, "name": f"{p.school} {p.program_name}",
                "facts": {n: self._fact_view(program_id, n) for n in OVERVIEW_FACTS}}

    def get_program_facts(self, program_id: str, fields: list[str] | None = None) -> dict:
        fields = [f for f in (fields or FACT_NAMES) if f in FACT_NAMES]
        self.store.get_program(program_id)
        return {"program_id": program_id, "facts": {n: self._fact_view(program_id, n) for n in fields}}

    def get_evidence(self, evidence_id: str) -> dict:
        return self.store.get_evidence(evidence_id)

    def compare_employment_metrics(self, program_ids: list[str], metric: str = "employment_rate") -> dict:
        if metric not in ("employment_rate", "median_base_salary"):
            raise ValueError("metric must be employment_rate or median_base_salary")
        for pid in program_ids:
            self.store.get_program(pid)
        return compare_metrics(self.store, program_ids, metric)

    def get_sponsorship_evidence(self, program_id: str, occupation: str | None = None, city: str | None = None) -> dict:
        from .sponsorship import get_sponsorship_evidence
        self.store.get_program(program_id)
        return get_sponsorship_evidence(program_id, occupation, city)

    # ----- dispatch -----
    def call(self, agent: str, name: str, raw_args: str) -> str:
        self.budget.check_tool()
        key = (name, " ".join((raw_args or "{}").split()))
        if key in self._cache:
            self.log(agent, name, {"args": raw_args, "ok": True, "cached_repeat": True})
            return self._cache[key]
        try:
            args = json.loads(raw_args or "{}")
            if name not in self._impl:
                raise ValueError(f"unknown tool {name}")
            result = self._impl[name](**args)
            out = json.dumps({"note": UNTRUSTED_NOTE, "data": result}, default=str)
            self.log(agent, name, {"args": args, "ok": True, "result_size": len(out)})
            self._cache[key] = out
            self.by_agent.setdefault(agent, []).append({"tool": name, "args": args, "result": result})
            return out
        except (EvidenceNotFoundError, ValueError, TypeError, json.JSONDecodeError) as e:
            self.log(agent, name, {"args": raw_args, "ok": False, "error": str(e)[:200]})
            return json.dumps({"error": str(e)[:200]})

    # ----- OpenAI tool specs -----
    SPECS = {
        "search_programs": {
            "description": "Filter programs in the local evidence store by verified attributes. Unknown values never match.",
            "parameters": {"type": "object", "properties": {
                "stem_designated": {"type": "boolean"},
                "max_cost_of_attendance": {"type": "number", "description": "USD per year"},
                "states": {"type": "array", "items": {"type": "string"}, "description": "Two-letter US states"}},
                "additionalProperties": False}},
        "get_program_overview": {
            "description": "Key facts (location, tuition, cost, STEM, employment, test policy) with status and evidence ids.",
            "parameters": {"type": "object", "properties": {"program_id": {"type": "string"}},
                           "required": ["program_id"], "additionalProperties": False}},
        "get_program_facts": {
            "description": "Specific facts for one program with status, value, period, definition, evidence ids, verification level, freshness.",
            "parameters": {"type": "object", "properties": {
                "program_id": {"type": "string"},
                "fields": {"type": "array", "items": {"type": "string", "enum": list(FACT_NAMES)}}},
                "required": ["program_id"], "additionalProperties": False}},
        "get_evidence": {
            "description": "Source URL, title, excerpt, and verification level for one evidence id.",
            "parameters": {"type": "object", "properties": {"evidence_id": {"type": "string"}},
                           "required": ["evidence_id"], "additionalProperties": False}},
        "compare_employment_metrics": {
            "description": "Deterministically check whether programs' employment metrics share cohort year and definition.",
            "parameters": {"type": "object", "properties": {
                "program_ids": {"type": "array", "items": {"type": "string"}, "minItems": 2},
                "metric": {"type": "string", "enum": ["employment_rate", "median_base_salary"]}},
                "required": ["program_ids", "metric"], "additionalProperties": False}},
        "get_sponsorship_evidence": {
            "description": ("Historical H-1B LCA filings (U.S. DOL) by employers that the program's OFFICIAL employment report says hired "
                            "its graduates, filtered by target occupation and city. Each count has an evidence id (lca-...). Past filings "
                            "are history, never a promise that an employer will sponsor any person or role."),
            "parameters": {"type": "object", "properties": {
                "program_id": {"type": "string"},
                "occupation": {"type": "string", "enum": ["management_consulting", "product_management", "corporate_finance_strategy"]},
                "city": {"type": "string", "enum": ["Boston", "Seattle", "Houston", "New York", "San Francisco Bay Area"]}},
                "required": ["program_id"], "additionalProperties": False}},
    }

    def specs(self, names: tuple[str, ...]) -> list[dict]:
        return [{"type": "function", "function": {"name": n, **self.SPECS[n]}} for n in names]
