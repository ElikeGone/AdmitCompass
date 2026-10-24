"""Tokenomics from the CLEAN Task 3 live runs (Portkey cache force-refreshed on every request).

Reads the newest saved run for each demo fixture in experiments/agent_runs/, and writes clean_runs_analysis.json and
clean_runs_analysis.md here. No model calls.

Prices: set ADMITCOMPASS_PRICE_INPUT_PER_MTOK, ADMITCOMPASS_PRICE_CACHED_INPUT_PER_MTOK and
ADMITCOMPASS_PRICE_OUTPUT_PER_MTOK (USD per 1M tokens) plus ADMITCOMPASS_PRICE_SOURCE in .env to use a real price.
Without them, only the clearly labeled HYPOTHETICAL scenarios are reported.

    .venv\\Scripts\\python experiments\\tokenomics\\analyze_clean_runs.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.core.config import load_environment  # noqa: E402

RUNS = ROOT / "experiments" / "agent_runs"
OUT = Path(__file__).resolve().parent
FIXTURES = ["fixture-audit-consulting-ghana", "fixture-domestic-tech-us"]
HYPOTHETICAL = {
    "H1 low (hypothetical)": {"input": 0.50, "cached_input": 0.05, "output": 2.00},
    "H2 mid (hypothetical)": {"input": 2.00, "cached_input": 0.20, "output": 8.00},
    "H3 high (hypothetical)": {"input": 5.00, "cached_input": 0.50, "output": 20.00},
}
RUNS_PER_USER_PER_MONTH = 3  # stated assumption: an applicant re-runs after editing their profile a couple of times


def newest(profile_id: str) -> Path | None:
    dirs = sorted(d for d in RUNS.iterdir() if d.is_dir() and d.name.endswith("_" + profile_id))
    return dirs[-1] if dirs else None


def per_agent(trace: list) -> dict:
    out = {}
    for e in trace:
        if e["kind"] != "llm_call":
            continue
        d = e["detail"]
        a = out.setdefault(e["agent"], {"requests": 0, "input": 0, "cached_input": 0, "output": 0, "reasoning": 0, "model_seconds": 0.0})
        a["requests"] += 1
        a["input"] += d.get("input_tokens") or 0
        a["cached_input"] += d.get("cached_input_tokens") or 0
        a["output"] += d.get("output_tokens") or 0
        a["reasoning"] += d.get("reasoning_tokens") or 0
        a["model_seconds"] = round(a["model_seconds"] + (d.get("elapsed_seconds") or 0), 2)
    return out


def cost(inp: int, cached: int, out: int, p: dict) -> float:
    return ((inp - cached) * p["input"] + cached * p["cached_input"] + out * p["output"]) / 1e6


def price_settings() -> tuple[dict | None, str | None]:
    load_environment(ROOT)
    keys = {"input": "ADMITCOMPASS_PRICE_INPUT_PER_MTOK", "cached_input": "ADMITCOMPASS_PRICE_CACHED_INPUT_PER_MTOK",
            "output": "ADMITCOMPASS_PRICE_OUTPUT_PER_MTOK"}
    vals = {k: os.getenv(v, "").strip() for k, v in keys.items()}
    if all(vals.values()):
        return {k: float(v) for k, v in vals.items()}, os.getenv("ADMITCOMPASS_PRICE_SOURCE", "not stated")
    return None, None


def projections(per_run: float) -> dict:
    return {"per_run": round(per_run, 5), "per_user_month": round(per_run * RUNS_PER_USER_PER_MONTH, 4),
            "users_100_month": round(per_run * RUNS_PER_USER_PER_MONTH * 100, 2),
            "users_10000_month": round(per_run * RUNS_PER_USER_PER_MONTH * 10000, 2)}


def main() -> int:
    runs = {}
    # every clean (cache force-refreshed) run of the two demo fixtures: command-line and saved web-UI runs
    dirs = sorted(d for d in RUNS.iterdir() if d.is_dir() and d.name >= "20261024T" and any(f"_{p}" in d.name for p in FIXTURES))
    for d in dirs:
        summ = json.loads((d / "usage_summary.json").read_text(encoding="utf-8"))
        trace = json.loads((d / "trace.json").read_text(encoding="utf-8"))
        t = summ["totals"]
        runs[d.name] = {"run_dir": d.name, "status": summ["status"], "revision_performed": summ["revision_performed"],
                     "totals": {k: t.get(k) for k in ("model_requests", "input_tokens", "cached_input_tokens", "output_tokens",
                                                      "reasoning_tokens_within_output", "tool_calls", "model_seconds", "wall_seconds")},
                     "per_agent": per_agent(trace)}
    if not runs:
        return 1
    n = len(runs)
    avg = {k: sum(r["totals"][k] or 0 for r in runs.values()) / n for k in ("input_tokens", "cached_input_tokens", "output_tokens")}
    real, source = price_settings()
    priced = {}
    if real:
        priced["configured price"] = {"usd_per_mtok": real, "price_source": source,
                                      **projections(cost(avg["input_tokens"], avg["cached_input_tokens"], avg["output_tokens"], real))}
    for name, p in HYPOTHETICAL.items():
        priced[name] = {"usd_per_mtok": p, **projections(cost(avg["input_tokens"], avg["cached_input_tokens"], avg["output_tokens"], p))}
    analysis = {
        "runs": runs, "average_run_tokens": {k: round(v) for k, v in avg.items()},
        "cache": "Portkey header x-portkey-cache-force-refresh: true on every request (PORTKEY_CACHE_FORCE_REFRESH=1).",
        "price": ("Configured price from .env" if real else
                  "UNKNOWN — no documented gpt-6-luna price was found; all dollar figures are HYPOTHETICAL scenarios."),
        "formula": "cost_per_run = (input - cached) * P_in + cached * P_cached + output * P_out",
        "assumption_runs_per_user_per_month": RUNS_PER_USER_PER_MONTH, "cost_projections": priced,
    }
    (OUT / "clean_runs_analysis.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    md = ["# Tokenomics — clean live runs (Task 3)", "",
          "Runs: " + ", ".join(f"`{r['run_dir']}` ({r['status']})" for r in runs.values()) + ". Portkey's cache was force-refreshed on every request, so these tokens are fresh generations.", "",
          "\"Cached input\" is the model provider's own prompt caching inside a run (an agent's repeated system prompt and history "
          "on its follow-up tool calls), reported by the API's usage field. It is not a replay of an earlier response.", "",
          "## Tokens per run", "", "| Run | Requests | Input | Cached input | Output | (reasoning) | Tool calls | Wall s |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for pid, r in runs.items():
        t = r["totals"]
        md.append(f"| {pid} | {t['model_requests']} | {t['input_tokens']:,} | {t['cached_input_tokens']:,} | {t['output_tokens']:,} | {t['reasoning_tokens_within_output']:,} | {t['tool_calls']} | {t['wall_seconds']} |")
    md += ["", "## Tokens per agent", ""]
    for pid, r in runs.items():
        md += [f"**{pid}**", "", "| Agent | Requests | Input | Cached input | Output | (reasoning) | Model s |", "|---|---:|---:|---:|---:|---:|---:|"]
        md += [f"| {a} | {v['requests']} | {v['input']:,} | {v['cached_input']:,} | {v['output']:,} | {v['reasoning']:,} | {v['model_seconds']} |" for a, v in r["per_agent"].items()]
        md.append("")
    md += ["## Cost", "", f"Price: {analysis['price']}", "", f"Formula: `{analysis['formula']}`. Assumption: {RUNS_PER_USER_PER_MONTH} runs per user per month.", "",
           "| Price set | $/1M in · cached · out | Per run | Per user / month | 100 users / month | 10,000 users / month |", "|---|---|---:|---:|---:|---:|"]
    for name, c in priced.items():
        p = c["usd_per_mtok"]
        md.append(f"| {name} | {p['input']} · {p['cached_input']} · {p['output']} | ${c['per_run']} | ${c['per_user_month']} | ${c['users_100_month']:,} | ${c['users_10000_month']:,} |")
    (OUT / "clean_runs_analysis.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
