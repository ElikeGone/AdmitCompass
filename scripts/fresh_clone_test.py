"""Fresh-clone test (Windows, macOS, Linux):  python scripts/fresh_clone_test.py [--repo-url URL] [--port 8766]

Simulates the teaching-staff setup in a brand-new temporary folder:
  1. `git clone` the repo URL (or, without --repo-url, clone this local repository's committed HEAD);
  2. put a .env ONE FOLDER ABOVE the clone (placeholder key + Ask AI mock mode: no real secret, no billable call);
  3. follow README.md exactly: create a venv, `pip install -r requirements.txt`, start uvicorn;
  4. check /health, the homepage and /api/programs, and append the result and timings to experiments/fresh_clone_test.md.

(Replaces an earlier PowerShell version that Windows Defender flagged as a false positive on checkout.)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
LOG = SRC / "experiments" / "fresh_clone_test.md"


def get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception:   # noqa: BLE001 - any failure just means "not ready / not ok"
        return 0, ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-url", default="")
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--keep", action="store_true", help="keep the temporary folder")
    a = ap.parse_args()
    t0 = time.perf_counter()
    step = lambda m: print(f"[{int(time.perf_counter() - t0)}s] {m}", flush=True)   # noqa: E731
    work = Path(tempfile.mkdtemp(prefix="acclone-"))
    repo = work / "AdmitCompass"
    source = a.repo_url or str(SRC)
    step(f"git clone {source}")
    subprocess.run(["git", "clone", "--quiet", "--depth", "1", source if a.repo_url else SRC.as_uri(), str(repo)], check=True)
    (work / ".env").write_text("PORTKEY_API_KEY=fresh-clone-placeholder-not-a-real-key\nAC_COPILOT_MODE=mock\n", encoding="ascii")
    step(f".env placed one folder ABOVE the repo: {work / '.env'}")
    py = repo / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    step("README: create venv"); subprocess.run([sys.executable, "-m", "venv", str(repo / ".venv")], check=True)
    step("README: pip install -r requirements.txt")
    subprocess.run([str(py), "-m", "pip", "install", "-q", "-r", "requirements.txt"], cwd=repo, check=True)
    t_install = int(time.perf_counter() - t0)
    step(f"README: start uvicorn on port {a.port}")
    server = subprocess.Popen([str(py), "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(a.port)],
                              cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    health = None
    try:
        for _ in range(90):
            code, body = get(f"http://127.0.0.1:{a.port}/health")
            if code == 200:
                health = json.loads(body); break
            time.sleep(1)
        t_ready = int(time.perf_counter() - t0)
        home, _ = get(f"http://127.0.0.1:{a.port}/")
        progs, _ = get(f"http://127.0.0.1:{a.port}/api/programs")
    finally:
        server.terminate()
        try: server.wait(10)
        except subprocess.TimeoutExpired: server.kill()
    ok = bool(health) and health.get("status") == "ok"
    key = bool(health) and health.get("api_key_configured") is True
    result = "PASS" if ok and key and home == 200 and progs == 200 and t_ready <= 600 else "FAIL"
    step(f"health ok={ok} api_key_configured={key} home={home} programs={progs} -> {result}")
    pyv = subprocess.run([str(py), "--version"], capture_output=True, text=True).stdout.strip()
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"\n## {datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ} - {result} ({sys.platform}, Python script)\n"
                f"- Mode: git clone of {'the repo URL' if a.repo_url else 'the local repository HEAD'}; {pyv}\n"
                f"- .env one folder above the repo; /health ok={ok}, api_key_configured={key}; GET / = {home}; GET /api/programs = {progs}\n"
                f"- Time to installed: {t_install}s; time to app answering /health: {t_ready}s (limit: 600s)\n")
    if not a.keep:
        shutil.rmtree(work, ignore_errors=True)
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
