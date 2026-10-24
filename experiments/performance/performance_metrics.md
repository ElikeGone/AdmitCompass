# Local performance metrics (non-LLM)

Script: `.venv\Scripts\python experiments\performance\measure.py` → `performance_metrics.json` (measured 2026-10-23).
Machine: Windows 11 Pro, Python 3.14.7 (details in the JSON). Method: wall-clock `time.perf_counter()`; real HTTP to a local uvicorn process via `urllib`; one warm-up request per endpoint excluded; no model calls.

| Measurement | n | Median | Range (min–max) | p90 |
|---|---|---|---|---|
| App startup: spawn uvicorn → first `/health` OK (includes imports) | 5 | 2,620 ms | 2,604–2,700 ms | 2,638 ms |
| `GET /health` | 50 | 3.7 ms | 1.9–28.4 ms | 16.8 ms |
| `GET /api/config` | 50 | 2.1 ms | 1.9–26.5 ms | 4.1 ms |
| `GET /api/fixtures` | 50 | 5.9 ms | 3.8–32.6 ms | 18.0 ms |
| `GET /api/demo` (saved run + evidence map, 87 KB) | 50 | 7.0 ms | 5.1–24.7 ms | 8.9 ms |
| `GET /` (app shell) | 50 | 3.6 ms | 3.0–24.5 ms | 7.0 ms |
| `GET /static/app.js` (61 KB) | 50 | 5.8 ms | 4.1–31.2 ms | 8.0 ms |
| Evidence store: load + full Pydantic validation of 6 programs / 49 sources | 20 | 8.2 ms | 6.1–12.6 ms | 10.7 ms |
| `get_fact` (fact + evidence + source + freshness) | 2,000 | 0.01 ms | 0.01–0.46 ms | 0.02 ms |
| `filter_programs` (STEM + cost filter) | 200 | 0.01 ms | 0.01–0.04 ms | 0.01 ms |
| Post-run audit `scripts/verify_run.py` (whole CLI process) | 20 | 702 ms | 653–751 ms | 728 ms |

**Interpretation:** every deterministic part of the system (evidence retrieval, validation, API, audit) takes milliseconds. End-to-end latency is dominated by model calls: 50.7 s in the real run, with about 2.6 s of server startup on top for a cold start. The audit's ~0.7 s is mostly Python start-up and imports.

**Limitations:** one machine; localhost only (no network latency); small dataset (6 programs), so retrieval times reflect in-memory lookups.
