"""Local, non-LLM performance measurements. No model calls.

Measures: app startup (cold uvicorn process until /health answers), API response times over real HTTP,
demo loading, evidence retrieval, and deterministic report verification.
Usage: .venv\\Scripts\\python experiments\\performance\\measure.py
"""
from __future__ import annotations

import json
import os
import platform
import socket
import statistics
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent
PY = sys.executable


def stats(xs_ms: list[float]) -> dict:
    return {"n": len(xs_ms), "median_ms": round(statistics.median(xs_ms), 2), "min_ms": round(min(xs_ms), 2),
            "max_ms": round(max(xs_ms), 2), "p90_ms": round(sorted(xs_ms)[int(0.9 * (len(xs_ms) - 1))], 2)}


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read()


def measure_startup(n: int = 5) -> dict:
    times = []
    for _ in range(n):
        port = free_port()
        t = time.perf_counter()
        proc = subprocess.Popen([PY, "-m", "uvicorn", "backend.app.main:app", "--port", str(port), "--log-level", "warning"],
                                cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            while True:
                try:
                    get(f"http://127.0.0.1:{port}/health")
                    break
                except Exception:
                    if time.perf_counter() - t > 30:
                        raise RuntimeError("server did not start")
                    time.sleep(0.02)
            times.append((time.perf_counter() - t) * 1000)
        finally:
            proc.terminate()
            proc.wait(10)
    return {**stats(times), "what": "spawn uvicorn process -> first successful GET /health (includes Python import time)"}


def measure_http(n: int = 50) -> dict:
    port = free_port()
    proc = subprocess.Popen([PY, "-m", "uvicorn", "backend.app.main:app", "--port", str(port), "--log-level", "warning"],
                            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(500):
            try:
                get(f"http://127.0.0.1:{port}/health")
                break
            except Exception:
                time.sleep(0.02)
        out = {}
        for path in ("/health", "/api/config", "/api/fixtures", "/api/demo", "/", "/static/app.js"):
            get(f"http://127.0.0.1:{port}{path}")  # warm-up, not counted
            xs, size = [], 0
            for _ in range(n):
                t = time.perf_counter()
                body = get(f"http://127.0.0.1:{port}{path}")
                xs.append((time.perf_counter() - t) * 1000)
                size = len(body)
            out[path] = {**stats(xs), "response_bytes": size}
        return out
    finally:
        proc.terminate()
        proc.wait(10)


def measure_evidence(n: int = 2000) -> dict:
    from backend.app.tools.evidence_store import EvidenceStore
    t = time.perf_counter()
    store = EvidenceStore.load()
    load_ms = (time.perf_counter() - t) * 1000
    loads = []
    for _ in range(20):
        t = time.perf_counter()
        EvidenceStore.load()
        loads.append((time.perf_counter() - t) * 1000)
    xs = []
    for i in range(n):
        t = time.perf_counter()
        store.get_fact(["yale-som-mba", "chicago-booth-mba", "mit-sloan-mba"][i % 3], "cost_of_attendance")
        xs.append((time.perf_counter() - t) * 1000)
    fs = []
    for _ in range(200):
        t = time.perf_counter()
        store.filter_programs(stem_designated=True, max_cost_of_attendance=135000)
        fs.append((time.perf_counter() - t) * 1000)
    return {"first_load_ms": round(load_ms, 2), "load_and_validate_dataset": stats(loads),
            "get_fact_with_evidence_and_freshness": stats(xs), "filter_programs": stats(fs)}


def measure_verification(n: int = 20) -> dict:
    run_dir = ROOT / "experiments" / "agent_runs" / "20261023T180104Z_fixture-tech-pm-india"
    xs = []
    for _ in range(n):
        t = time.perf_counter()
        r = subprocess.run([PY, "scripts/verify_run.py", str(run_dir)], cwd=ROOT, capture_output=True)
        xs.append((time.perf_counter() - t) * 1000)
        assert r.returncode == 0
    return {**stats(xs), "what": "full CLI process: python start + imports + audit of the saved run"}


def main() -> int:
    res = {"measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "machine": {"os": platform.platform(), "python": platform.python_version(), "cpu_count": os.cpu_count()},
           "method": "Wall-clock time.perf_counter(); localhost HTTP via urllib; warm-up request excluded for HTTP; no model calls.",
           "startup": measure_startup(), "http_api": measure_http(), "evidence_store": measure_evidence(),
           "report_verification": measure_verification()}
    (OUT / "performance_metrics.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
