"""Run record for the developer/report view: what one analysis did, measured.

Built from the run's report, its public trace events (raw errors already replaced) and the evidence map. Privacy:
no profile fields and no tool-argument values that come from the profile (e.g. the budget passed to search_programs);
program ids, fact names and evidence ids are kept because they identify public sources, not the applicant.
No API keys exist anywhere in these inputs.
"""
from __future__ import annotations

from collections import Counter

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
        "estimated_cost": {"usd": totals.get("estimated_cost_usd"), "basis": totals.get("cost_basis")},
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
        ("Estimated cost", f"${cost['usd']:.4f}" if cost["usd"] is not None else f"not available — {cost['basis']}"),
        ("Sources cited", f"{len(rec['sources']['source_ids'])} sources · {len(rec['sources']['evidence_ids'])} evidence items"),
        ("Validation warnings", str(len(rec["validation_warnings"]))),
        ("Safety checks triggered", ", ".join(f"{k} ×{v}" for k, v in rec["safety_checks"]["grounding_rules_triggered"].items()) or "none"),
        ("Final recommendation", ", ".join(f"{s['program']} ({s['career_fit']})" for s in rec["final_recommendation"]["shortlist"]) or "none"),
    ]
