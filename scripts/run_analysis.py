"""Run one real multi-agent analysis on a FICTIONAL fixture and save sanitized evidence.

Usage: .venv\\Scripts\\python scripts\\run_analysis.py data\\fixtures\\applicant_tech_pm.json
Output: experiments/agent_runs/<UTC timestamp>_<profile_id>/
  input_profile.json, agent_outputs.json, trace.json, report.json, usage_summary.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.core.config import get_settings  # noqa: E402
from backend.app.core.llm import make_portkey_responses_chat  # noqa: E402
from backend.app.orchestrator import Orchestrator  # noqa: E402
from backend.app.schemas.applicant import ApplicantProfile  # noqa: E402
from backend.app.tools.evidence_store import EvidenceStore  # noqa: E402

OUT_ROOT = ROOT / "experiments" / "agent_runs"


def run(profile_path: Path) -> tuple[Path, dict]:
    profile = ApplicantProfile.model_validate_json(profile_path.read_text(encoding="utf-8"))
    if not profile.is_fictional:
        raise SystemExit("Refusing to save a run for a non-fictional profile.")
    settings = get_settings()
    from backend.app.tools.catalog import store_for_profile
    store = store_for_profile(EvidenceStore.load(), profile)   # fixtures are fictional -> 'detailed' programs only
    orch = Orchestrator(make_portkey_responses_chat(settings), store, model=settings.model)
    report = orch.run(profile)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = OUT_ROOT / f"{stamp}_{profile.profile_id}"
    out.mkdir(parents=True, exist_ok=True)

    def dump(name, obj):
        (out / name).write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")

    dump("input_profile.json", profile.model_dump(mode="json"))
    dump("agent_outputs.json", {k: v.model_dump(mode="json") for k, v in orch.outputs.items()})
    dump("trace.json", [e.model_dump(mode="json") for e in orch.trace])
    dump("report.json", report.model_dump(mode="json"))
    summary = {"run_id": report.run_id, "status": report.status, "model": report.model,
               "revision_performed": report.revision_performed, "revision_target": report.revision_target,
               "grounding_violations": len(report.grounding_violations),
               "usage_by_agent": [u.model_dump() for u in report.usage_by_agent], "totals": report.totals,
               "error": report.error}
    dump("usage_summary.json", summary)
    return out, summary


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "fixtures" / "applicant_tech_pm.json"
    out_dir, summary = run(path)
    print(f"Saved to {out_dir}")
    print(json.dumps(summary, indent=2))
