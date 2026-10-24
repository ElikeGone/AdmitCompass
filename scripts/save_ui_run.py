"""Save a finished LIVE web-UI run (kept only in server memory) to experiments/agent_runs/ in the same format as
scripts/run_analysis.py, so UI runs can be audited and used for tokenomics. No model call.

    .venv\\Scripts\\python scripts\\save_ui_run.py <run_id> [http://127.0.0.1:8000]

(agent_outputs.json isn't available for UI runs; the report and trace contain the grounded outputs and all usage.)
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

run_id = sys.argv[1]
base = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8000"
d = httpx.get(f"{base}/api/runs/{run_id}", params={"since": 0}, timeout=30).json()
if "result" not in d:
    sys.exit(f"Run {run_id} has no result yet (status: {d.get('status')}).")
res, report = d["result"], d["result"]["report"]
profile = res["profile"]
if not profile.get("is_fictional"):
    sys.exit("Refusing to save a run for a non-fictional profile.")
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
out = Path(__file__).resolve().parents[1] / "experiments" / "agent_runs" / f"{stamp}_{profile['profile_id']}_webui"
out.mkdir(parents=True, exist_ok=True)


def dump(name, obj):
    (out / name).write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


dump("input_profile.json", profile)
dump("trace.json", res["events"])
dump("report.json", report)
dump("usage_summary.json", {"run_id": report["run_id"], "server_run_id": run_id, "source": "web UI (POST /api/runs)",
                            "status": report["status"], "model": report["model"], "revision_performed": report["revision_performed"],
                            "revision_target": report["revision_target"], "grounding_violations": len(report["grounding_violations"]),
                            "usage_by_agent": report["usage_by_agent"], "totals": report["totals"], "error": report.get("error"),
                            "server_budget_snapshot": d.get("budget")})
print(f"Saved to {out}")
print(json.dumps({"status": report["status"], "shortlist": [r["program_id"] for r in report["recommendations"]],
                  "requests": report["totals"]["model_requests"]}, indent=1))
