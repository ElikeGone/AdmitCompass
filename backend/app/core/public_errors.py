"""User-safe error objects for the public API.

Raw error text (Pydantic validation messages, exception strings, tool errors) stays in the in-memory run trace, the saved
developer run records under experiments/agent_runs/, and the server log (logger "admitcompass.errors"). The public API
returns only these structured objects: no prompt text, stack traces, schema internals, model output, keys or paths.
"""
from __future__ import annotations

import copy
import logging
import re

log = logging.getLogger("admitcompass.errors")

OUTPUT_VALIDATION_FAILED = {"status": "retryable_error", "error_code": "OUTPUT_VALIDATION_FAILED",
                            "message": "The analysis could not be validated. Please retry."}
TOOL_LOOKUP_FAILED = {"status": "handled", "error_code": "TOOL_LOOKUP_FAILED",
                      "message": "A data lookup failed; the agent was told and continued without it."}
UPSTREAM_UNAVAILABLE = {"status": "retryable_error", "error_code": "UPSTREAM_UNAVAILABLE",
                        "message": "The AI service didn't respond. Please retry."}
ANALYSIS_FAILED = {"status": "failed", "error_code": "ANALYSIS_FAILED",
                   "message": "The analysis stopped safely before finishing."}
BUDGET_LIMIT_REACHED = {"status": "stopped", "error_code": "BUDGET_LIMIT_REACHED",
                        "message": "The analysis reached its usage limit and stopped."}

# Budget reasons come from fixed templates in core/budget.py; anything else is replaced.
_BUDGET_REASON = re.compile(r"^(request|token|time|tool-call) limit reached \(\d+s?/\d+s?\)$")
_VALIDATION_HINT = re.compile(r"validation|ValidationError|JSONDecodeError|schema|failed format", re.I)
_UPSTREAM_HINT = re.compile(r"timeout|timed out|connection|APIConnection|RateLimit|\b50[234]\b|unavailable", re.I)


def public_error(raw: object, kind: str) -> dict | None:
    """kind: "validation" | "tool" | "failure" | "budget". Returns a fresh dict (never the raw text)."""
    if raw in (None, "") and kind != "validation":
        return None
    text = raw if isinstance(raw, str) else ""
    if kind == "validation":
        return dict(OUTPUT_VALIDATION_FAILED)
    if kind == "tool":
        return dict(TOOL_LOOKUP_FAILED)
    if kind == "budget":
        return dict(BUDGET_LIMIT_REACHED, reason=text) if _BUDGET_REASON.match(text) else dict(BUDGET_LIMIT_REACHED)
    if _VALIDATION_HINT.search(text):
        return dict(OUTPUT_VALIDATION_FAILED)
    if _UPSTREAM_HINT.search(text):
        return dict(UPSTREAM_UNAVAILABLE)
    return dict(ANALYSIS_FAILED)


def public_event(e: dict) -> dict:
    """Copy of a trace event with every raw error replaced by a structured, user-safe object."""
    e = copy.deepcopy(e)
    d = e.get("detail") or {}
    kind = e.get("kind")
    if "error" in d:
        d["error"] = public_error(d["error"], {"validation": "validation", "tool_call": "tool"}.get(kind, "failure"))
    d.pop("output_type", None)   # internal schema class name (e.g. "PathwayOutput")
    if kind == "budget_stop" and "reason" in d:
        d["reason"] = d["reason"] if isinstance(d["reason"], str) and _BUDGET_REASON.match(d["reason"]) else "usage limit reached"
    return e


def public_report(report: dict, status: str | None = None) -> dict:
    """Copy of a run report whose `error` is a structured object instead of raw text."""
    report = dict(report)
    if report.get("error"):
        st = status or report.get("status")
        report["error"] = public_error(report["error"], "budget" if st == "stopped_budget" else "failure")
    return report
