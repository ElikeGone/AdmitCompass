"""Tokenomics analysis of the REAL saved agent runs (provider-reported usage from Portkey/gpt-6-luna).

Writes experiments/tokenomics/tokenomics_analysis.json. No model calls.
Usage: .venv\\Scripts\\python experiments\\tokenomics\\analyze_runs.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "experiments" / "agent_runs"
OUT = Path(__file__).resolve().parent
COMPLETE = "20261023T180104Z_fixture-tech-pm-india"
EARLIER = "20261023T175556Z_fixture-tech-pm-india"

# HYPOTHETICAL price scenarios (USD per 1M tokens). NOT gpt-6-luna prices: no documented price was found in the
# course site, instructions page, or provider configuration (checked 2026-10-23).
SCENARIOS = {
    "H1 low (hypothetical)": {"input": 0.50, "cached_input": 0.05, "output": 2.00},
    "H2 mid (hypothetical)": {"input": 2.00, "cached_input": 0.20, "output": 8.00},
    "H3 high (hypothetical)": {"input": 5.00, "cached_input": 0.50, "output": 20.00},
}
RUNS_PER_USER_PER_MONTH = 3  # assumption: an applicant re-runs after editing their profile a couple of times


def llm_calls(trace):
    return [e for e in trace if e["kind"] == "llm_call"]


def per_agent(trace):
    out = {}
    for e in llm_calls(trace):
        d, a = e["detail"], out.setdefault(e["agent"], {"requests": 0, "input": 0, "cached": 0, "output": 0, "reasoning": 0, "seconds": 0.0})
        a["requests"] += 1
        a["input"] += d.get("input_tokens") or 0
        a["cached"] += d.get("cached_input_tokens") or 0
        a["output"] += d.get("output_tokens") or 0
        a["reasoning"] += d.get("reasoning_tokens") or 0
        a["seconds"] = round(a["seconds"] + (d.get("elapsed_seconds") or 0), 3)
    return out


def overhead(trace):
    """Tokens spent on retries: schema retries (attempt 2) and grounding retries (all calls after a retry event)."""
    after_retry, res = set(), {"schema_retry": {"requests": 0, "input": 0, "output": 0}, "grounding_retry": {"requests": 0, "input": 0, "output": 0}}
    for e in trace:
        d = e["detail"]
        if e["kind"] == "grounding" and d.get("retry"):
            after_retry.add(e["agent"])
        if e["kind"] == "handoff":
            after_retry.discard(e["agent"])
        if e["kind"] != "llm_call":
            continue
        bucket = "grounding_retry" if e["agent"] in after_retry else "schema_retry" if d.get("attempt", 1) > 1 else None
        if bucket:
            res[bucket]["requests"] += 1
            res[bucket]["input"] += d.get("input_tokens") or 0
            res[bucket]["output"] += d.get("output_tokens") or 0
    return res


def repeated_tools(trace):
    seen, repeats = {}, []
    for e in trace:
        if e["kind"] != "tool_call":
            continue
        args = e["detail"]["args"]
        key = (e["detail"]["tool"], json.dumps(args if isinstance(args, dict) else json.loads(args), sort_keys=True))
        if key in seen:
            repeats.append({"seq": e["seq"], "agent": e["agent"], "tool": key[0], "first_seq": seen[key],
                            "served_from_run_cache": bool(e["detail"].get("cached_repeat"))})
        else:
            seen[key] = e["seq"]
    return repeats


def cost(inp, cached, out, p):
    return ((inp - cached) * p["input"] + cached * p["cached_input"] + out * p["output"]) / 1e6


def main() -> int:
    tc = json.loads((RUNS / COMPLETE / "trace.json").read_text(encoding="utf-8"))
    te = json.loads((RUNS / EARLIER / "trace.json").read_text(encoding="utf-8"))
    summ = json.loads((RUNS / COMPLETE / "usage_summary.json").read_text(encoding="utf-8"))
    calls_c, calls_e = llm_calls(tc), llm_calls(te)
    sig = lambda d: (d["input_tokens"], d["cached_input_tokens"], d["output_tokens"], d.get("reasoning_tokens"))  # noqa: E731
    identical = [i + 1 for i, (a, b) in enumerate(zip(calls_c, calls_e)) if sig(a["detail"]) == sig(b["detail"])]
    fast_identical = [i for i in identical if calls_c[i - 1]["detail"]["elapsed_seconds"] < 1.0]
    t = summ["totals"]
    fresh = calls_c[len(identical):] if identical == list(range(1, len(identical) + 1)) else []
    fresh_tot = {k: sum(c["detail"].get(f) or 0 for c in fresh) for k, f in
                 (("input", "input_tokens"), ("cached", "cached_input_tokens"), ("output", "output_tokens"))}
    scen = {}
    for name, p in SCENARIOS.items():
        per_run = cost(t["input_tokens"], t["cached_input_tokens"], t["output_tokens"], p)
        scen[name] = {"usd_per_mtok": p, "per_run": round(per_run, 4),
                      "per_user_month": round(per_run * RUNS_PER_USER_PER_MONTH, 4),
                      "users_100_month": round(per_run * RUNS_PER_USER_PER_MONTH * 100, 2),
                      "users_10000_month": round(per_run * RUNS_PER_USER_PER_MONTH * 10000, 2)}
    analysis = {
        "source_runs": {"complete": COMPLETE, "earlier_budget_stopped": EARLIER},
        "price": "UNKNOWN — no documented gpt-6-luna price (course site, instructions page, provider config checked 2026-10-23). All dollar figures below are hypothetical scenarios.",
        "complete_run_totals": {k: t[k] for k in ("model_requests", "input_tokens", "cached_input_tokens", "output_tokens",
                                                  "reasoning_tokens_within_output", "tool_calls", "model_seconds", "wall_seconds")},
        "cached_share_of_input_pct": round(100 * t["cached_input_tokens"] / t["input_tokens"], 1),
        "per_agent_complete_run": per_agent(tc),
        "per_agent_earlier_run": per_agent(te),
        "retry_overhead_complete_run": overhead(tc),
        "repeated_tool_calls_complete_run": repeated_tools(tc),
        "cache_replay_evidence": {
            "requests_with_identical_usage_to_earlier_run": identical,
            "of_which_under_1s": fast_identical,
            "interpretation": (f"Requests {identical[0]}-{identical[-1]} of the complete run reported byte-identical token usage to "
                               f"the earlier run ({len(fast_identical)} of them in under 1 s). This is consistent with Portkey serving "
                               "identical requests from a response cache. "
                               "The complete run is therefore NOT a clean fresh-generation benchmark: only the later requests are "
                               "certainly fresh. Whether replayed requests are billed is unknown."),
            "certainly_fresh_requests": len(fresh), "certainly_fresh_tokens": fresh_tot,
        },
        "formula": "cost_per_run = (input - cached) * P_in + cached * P_cached + output * P_out   (P in USD per token)",
        "assumption_runs_per_user_per_month": RUNS_PER_USER_PER_MONTH,
        "hypothetical_cost_scenarios_using_complete_run_tokens": scen,
    }
    (OUT / "tokenomics_analysis.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    print(json.dumps({k: analysis[k] for k in ("complete_run_totals", "retry_overhead_complete_run", "cache_replay_evidence")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
