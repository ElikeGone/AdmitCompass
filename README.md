# AdmitCompass

AdmitCompass is a career-first MBA advisor for international applicants: four AI agents (Pathway Matcher, Evidence Analyst, Strategy Planner, Skeptic) turn an applicant's background and goal into a shortlist, a sourced evidence dossier and a week-by-week application plan. Every school fact is either verified from an official source (with link and date) or shown as unknown, and employer visa evidence comes from U.S. Department of Labor H-1B filings — never presented as a promise.

MGT 409 — AI Foundations for Managers, final project. Model: `gpt-6-luna` through Portkey (course key).

## Quick start (about 5 minutes)

Requirements: **Python 3.10 or newer** (tested on 3.10, 3.11 and 3.14) and internet access for the first install.

**1. Put the key in a `.env` file** — either in this repo folder **or one folder above it** (the app checks `./.env` first, then `../.env`):
```
PORTKEY_API_KEY=your-course-key
```
Everything else has defaults; `.env.example` lists every setting. Without a key the app still runs (Explore, the saved sample analysis, the dashboard, accounts); only new live analyses and live Ask AI answers need the key. To try Ask AI with no key and no cost, add `AC_COPILOT_MODE=mock` to the same `.env` (answers are labeled as mock).

**2. Install and start**

Windows (PowerShell or Command Prompt):
```
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

macOS / Linux:
```
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

**3. Open http://127.0.0.1:8000.** Check http://127.0.0.1:8000/health — it should show `"status": "ok"` and `"api_key_configured": true`.

## What to try
| Where | What |
|---|---|
| **Sample Analysis** (top menu) | A saved real four-agent run for a fictional applicant from Ghana (a second sample, from India, is linked on the page) — no cost to view |
| **Find my pathway** → *Use a sample applicant* → *Run my analysis* | A live four-agent run (~1–2 minutes, capped at 25 model requests / 200k tokens) |
| **Explore Programs** | 30 MBA programs with official facts, cost lines (official vs. estimates) and historical employer H-1B filings |
| **Ask AI** (top right, in the header) | A copilot that answers only from the evidence store, with citations; optional voice input in Chrome, Edge or Safari |
| **Sign Up / Sign In** (top right) | Accounts are on by default: saved programs, profile and weekly-task progress. The SQLite file `data/app/accounts.sqlite3` is created automatically (git-ignored); set `AC_ENABLE_ACCOUNTS=false` to turn accounts off. Guests can use everything else. |

Demo fixtures (fictional) are in `data/fixtures/`: `fixture-audit-consulting-ghana` (needs U.S. work authorization; consulting in Boston) and `fixture-domestic-tech-us` (U.S. citizen; product management in Seattle). Fictional demo profiles use only the 5 programs with detailed evidence (`AC_DEMO_DETAILED_ONLY=1`).

## Data, and the small test dataset
Everything the app needs is committed and small:
- `data/programs/programs.json` — 28 programs with verified facts and evidence; `data/programs/supplementary.json` — validated official extras and third-party cost estimates.
- `data/sponsorship/lca_filtered.csv` (~260 KB) — the **small test dataset** for employer H-1B evidence: U.S. DOL FY2025 LCA filings already filtered to three target occupations and five cities, with `provenance.json`.

The full DOL source files (~420 MB) are **not** in the repo. To rebuild the filtered dataset from them, follow `data/sponsorship/README.md` (download the four FY2025 quarterly files into `data/sponsorship/raw/`, then `python scripts/build_sponsorship.py`). The app itself never needs the raw files.

## Run the tests
```
.venv\Scripts\python -m pytest -q          (Windows)
.venv/bin/python -m pytest -q              (macOS / Linux)
```
All model calls in tests are mocked (no cost). Expected: all pass, 1 skipped (an optional live integration test). The voice-input JavaScript tests run through pytest when Node.js is installed and are skipped otherwise.

Fresh-clone check (any OS): `python scripts/fresh_clone_test.py [--repo-url <git url>]` clones into a new temporary folder, puts a placeholder `.env` one folder above it, follows the steps above and checks `/health` (results go to `experiments/fresh_clone_test.md`).

## Troubleshooting
| Symptom | Fix |
|---|---|
| `api_key_configured: false` on `/health` | The `.env` isn't in the repo folder or the folder directly above it, or the line isn't exactly `PORTKEY_API_KEY=...`. Restart the server after editing. |
| `python`/`py` not found | Install Python 3.10+ from python.org (Windows: tick "Add to PATH"), then reopen the terminal. |
| `pip install` fails behind a proxy | `python -m pip install --proxy http://host:port -r requirements.txt` |
| Port 8000 in use | Use `--port 8001` and open http://127.0.0.1:8001 |
| "This server allows 3 live analyses per session" | A safety cap on paid runs; restart the server, or raise `ADMITCOMPASS_MAX_LIVE_RUNS_PER_SERVER`. |
| Ask AI says it's unavailable | No key loaded. Set `AC_COPILOT_MODE=mock` to try it offline (answers are labeled as mock). |
| A page shows "Couldn't reach the server" | The server stopped; restart it with the start command above. |

## More
- Settings: `.env.example` · Development history: `docs/CHANGELOG.md` · Design decisions: `docs/decisions.md`
- Evidence for each rubric item: `docs/evidence_index.md` · Safety results: `experiments/safety/` · Token measurements: `experiments/tokenomics/`
- Decision support only — not admissions, legal or immigration advice. No admission odds; no sponsorship guarantees.
