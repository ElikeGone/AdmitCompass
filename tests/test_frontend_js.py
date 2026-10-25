"""Runs the frontend JavaScript tests (tests/js/*.test.mjs) with Node's built-in test runner.

They exercise frontend/voice.js against a mocked Web Speech API and a minimal fake DOM, so no browser, microphone or
network is needed. Skipped when Node.js isn't installed."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_voice_input_js():
    files = sorted(str(p) for p in (ROOT / "tests" / "js").glob("*.test.mjs"))
    assert files, "no JS test files found"
    r = subprocess.run(["node", "--test", *files], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout[-4000:] + r.stderr[-2000:]
