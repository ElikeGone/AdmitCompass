"""ONE real end-to-end run against gpt-6-luna. Costs money; skipped unless ADMITCOMPASS_LIVE_TEST=1."""
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.getenv("ADMITCOMPASS_LIVE_TEST") != "1", reason="live paid test; set ADMITCOMPASS_LIVE_TEST=1")


def test_live_full_agent_run():
    from scripts.run_analysis import run
    out_dir, summary = run(Path(__file__).resolve().parents[1] / "data" / "fixtures" / "applicant_tech_pm.json")
    assert (out_dir / "trace.json").exists() and (out_dir / "report.json").exists()
    assert summary["status"] in ("completed", "completed_with_violations"), summary["error"]
    assert summary["totals"]["input_tokens"] and summary["totals"]["output_tokens"]
