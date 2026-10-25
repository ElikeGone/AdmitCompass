"""Run record for the developer/report view: what one analysis did, measured.

Built from the run's report, its public trace events (raw errors already replaced) and the evidence map. Privacy:
no profile fields and no tool-argument values that come from the profile (e.g. the budget passed to search_programs);
program ids, fact names and evidence ids are kept because they identify public sources, not the applicant.
No API keys exist anywhere in these inputs.
"""
from __future__ import annotations

from collections import Counter

from ..core.usage import estimate_cost

# Projection scenarios: measured per-run values × number of analysis runs. Assumption (stated in the output): each user
# runs 4 full analyses a month; Ask AI questions are not included. These are estimates, never measurements.
RUNS_PER_USER_PER_MONTH = 4
SCENARIOS = [
    ("One run", 1),
    (f"One user, {RUNS_PER_USER_PER_MONTH} runs a month", RUNS_PER_USER_PER_MONTH),
    (f"100 users, {RUNS_PER_USER_PER_MONTH} runs each a month", 100 * RUNS_PER_USER_PER_MONTH),
    (f"10,000 users, {RUNS_PER_USER_PER_MONTH} runs each a month", 10_000 * RUNS_PER_USER_PER_MONTH),
]

AGENT_LABEL = {"pathway_matcher": "Pathway Matcher", "evidence_analyst": "Evidence Analyst", "strategy_planner": "Strategy Planner",
               "skeptic": "Skeptic", "orchestrator": "Orchestrator"}
PUBLIC_ARGS = {"program_id", "program_ids", "fields", "evidence_id", "metric", "occupation", "metro"}


def _args(args: object) -> dict:
    if not isinstance(args, dict):
        return {}
    return {k: (v if k in PUBLIC_ARGS else "[from profile]") for k, v in args.items() if v not in (None, [], "")}


def run_record(report: dict, events: list[dict], evidence: dict, verification: dict | None = None, mode: str = "live") -> dict:
    totals = report.get("totals") or {}
    steps, tools, warnings, safety = [], [], [], Counter()
    for e in events:
        k, a, d = e.get("kind"), e.get("agent"), e.get("detail") or {}
        if k == "agent_start":
            steps.append({"seq": e["seq"], "agent": AGENT_LABEL.get(a, a), "revision": bool(d.get("revision_feedback"))})
        elif k == "tool_call":
            tools.append({"seq": e["seq"], "agent": AGENT_LABEL.get(a, a), "tool": d.get("tool"), "args": _args(d.get("args")),
                          "ok": d.get("ok", True), "cached_repeat": bool(d.get("cached_repeat"))})
        elif k == "validation" and d.get("ok") is False:
            err = d.get("error") if isinstance(d.get("error"), dict) else {}
            warnings.append({"seq": e["seq"], "agent": AGENT_LABEL.get(a, a), "check": "output format",
                             "code": err.get("error_code", "OUTPUT_VALIDATION_FAILED"), "result": "retried"})
        elif k == "grounding" and d.get("violations"):
            for r in d.get("rules", []):
                safety[r] += 1
    for v in report.get("grounding_violations") or []:
        warnings.append({"agent": AGENT_LABEL.get(v.get("agent"), v.get("agent")), "check": "grounding", "code": v.get("rule"),
                         "result": v.get("action")})
    source_ids = sorted({x["source_id"] for x in evidence.values() if isinstance(x, dict) and x.get("source_id")})
    evidence_ids = sorted(i for i, x in evidence.items() if isinstance(x, dict) and not x.get("missing"))
    recs = report.get("recommendations") or []
    strategy = report.get("strategy") or {}
    return {
        "record_version": 1, "mode": mode, "run_id": report.get("run_id"), "status": report.get("status"),
        "model": report.get("model"), "reasoning_effort": totals.get("reasoning_effort"),
        "agent_steps": steps,
        "tool_calls": {"count": len(tools), "by_tool": dict(Counter(t["tool"] for t in tools)), "calls": tools},
        "sources": {"source_ids": source_ids, "evidence_ids": evidence_ids},
        "tokens": {"input": totals.get("input_tokens"), "cached_input": totals.get("cached_input_tokens"),
                   "output": totals.get("output_tokens"), "reasoning_within_output": totals.get("reasoning_tokens_within_output"),
                   "by_agent": [{"agent": AGENT_LABEL.get(u["agent"], u["agent"]), "requests": u.get("calls"), "input": u.get("input_tokens"),
                                 "cached_input": u.get("cached_input_tokens"), "output": u.get("output_tokens"),
                                 "model_seconds": u.get("elapsed_seconds")} for u in report.get("usage_by_agent") or []]},
        "requests": totals.get("model_requests"),
        "latency_seconds": {"wall": totals.get("wall_seconds"), "model": totals.get("model_seconds")},
        "estimated_cost": cost_block(report.get("model"), totals),
        "projections": projections(report.get("model"), totals),
        "validation_warnings": warnings,
        "safety_checks": {"grounding_rules_triggered": dict(safety),
                          "post_run_audit": (None if verification is None else ("passed" if verification.get("ok") else "problems found")),
                          "skeptic_revision": report.get("revision_target") if report.get("revision_performed") else None},
        "final_recommendation": {"shortlist": [{"program_id": r["program_id"], "program": r.get("program_name"), "career_fit": r.get("career_fit")}
                                               for r in recs],
                                 "excluded_count": len(report.get("excluded_programs") or []),
                                 "test_guidance": (strategy.get("test_guidance") or {}).get("recommendation")},
        "privacy": "No API keys, no profile fields; tool arguments that came from the profile are replaced with '[from profile]'.",
    }


def _measured_range() -> str:
    """Spread of input tokens across the saved real runs in experiments/agent_runs (read, never invented)."""
    import json
    from pathlib import Path
    vals = []
    for f in (Path(__file__).resolve().parents[3] / "experiments" / "agent_runs").glob("*/report.json"):
        try:
            v = (json.loads(f.read_text(encoding="utf-8")).get("totals") or {}).get("input_tokens")
        except (OSError, ValueError):
            continue
        if isinstance(v, int):
            vals.append(v)
    return f" (the {len(vals)} saved runs used {min(vals):,}–{max(vals):,} input tokens, including runs stopped at the budget cap)" if len(vals) >= 2 else ""


def cost_block(model: str | None, totals: dict) -> dict:
    """Cost of the measured run. Only computed from a documented price (core.usage.PRICES_PER_MTOK); otherwise
    'not calculated' — a price is never invented."""
    usd, basis = estimate_cost(model or "", totals.get("input_tokens"), totals.get("cached_input_tokens"), totals.get("output_tokens"))
    if usd is None:
        return {"usd": None, "status": "not calculated", "basis": f"not calculated — no documented {model or 'model'} price is configured"}
    return {"usd": usd, "status": "calculated", "basis": basis}


def projections(model: str | None, totals: dict) -> dict:
    """ESTIMATES for several usage levels: each measured per-run figure × the number of runs. Not measurements."""
    per = {k: totals.get(k) for k in ("model_requests", "input_tokens", "cached_input_tokens", "output_tokens")}
    rows = []
    for label, runs in SCENARIOS:
        scaled = {k: (v * runs if isinstance(v, (int, float)) else None) for k, v in per.items()}
        cost = cost_block(model, {**totals, **scaled})
        rows.append({"scenario": label, "runs": runs, **scaled, "estimated_cost_usd": cost["usd"], "cost_status": cost["status"]})
    return {"kind": "estimate",
            "method": "measured value for this one run × number of runs (linear scaling)",
            "formula": {"model_requests": "requests_per_run × runs", "input_tokens": "input_tokens_per_run × runs",
                        "cached_input_tokens": "cached_input_tokens_per_run × runs", "output_tokens": "output_tokens_per_run × runs",
                        "cost_usd": "((input − cached) × price_input + cached × price_cached_input + output × price_output) ÷ 1,000,000 — only with a documented price"},
            "assumptions": [f"Each user runs {RUNS_PER_USER_PER_MONTH} full analyses a month.",
                            "Every run uses as many tokens as this measured run; real runs vary" + _measured_range() + ".",
                            "Ask AI questions, retries and caching changes between runs are not included."],
            "rows": rows}


def run_summary(rec: dict) -> list[tuple[str, str]]:
    """Readable lines for the screenshot view."""
    t, lat, cost = rec["tokens"], rec["latency_seconds"], rec["estimated_cost"]
    fmt = lambda n: "—" if n is None else f"{n:,}"   # noqa: E731
    return [
        ("Model", f"{rec['model']} (reasoning effort: {rec.get('reasoning_effort') or '—'})"),
        ("Status", rec["status"] or "—"),
        ("Agent steps", " → ".join(s["agent"] + (" (revision)" if s["revision"] else "") for s in rec["agent_steps"]) or "—"),
        ("Model requests · tool calls", f"{fmt(rec['requests'])} · {rec['tool_calls']['count']}"),
        ("Tokens", f"{fmt(t['input'])} input ({fmt(t['cached_input'])} cached) · {fmt(t['output'])} output"),
        ("Latency", f"{lat['wall']} s total · {lat['model']} s in the model"),
        ("Estimated cost", f"${cost['usd']:.4f} ({cost['basis']})" if cost["usd"] is not None else "Not calculated — no documented gpt-6-luna price"),
        ("Sources cited", f"{len(rec['sources']['source_ids'])} sources · {len(rec['sources']['evidence_ids'])} evidence items"),
        ("Validation warnings", str(len(rec["validation_warnings"]))),
        ("Safety checks triggered", ", ".join(f"{k} ×{v}" for k, v in rec["safety_checks"]["grounding_rules_triggered"].items()) or "none"),
        ("Final recommendation", ", ".join(f"{s['program']} ({s['career_fit']})" for s in rec["final_recommendation"]["shortlist"]) or "none"),
    ]
