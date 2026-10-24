# AdmitCompass — review build

AdmitCompass is a career-first MBA planning app: four AI agents plus a code orchestrator, an evidence store of official program facts, a saved sample analysis, a career dashboard, accounts, and an "Ask AI" copilot.

The review build runs **without any API key**:
- **Ask AI** uses an offline mock model, so every answer is labeled "[Mock model — no AI call was made]". Retrieval, citations and safety checks are the real code.
- **Live analyses** (the paid four-agent run) are refused with a clear message. The **saved sample analysis** shows a real earlier gpt-6-luna run.
- **Accounts** work, using a fresh temporary SQLite database created at startup and deleted on exit.

## Requirements
- Linux or macOS with **Python 3.12 or newer** (developed on 3.14).
- Internet access on first start, to install the Python packages.

## Start (Linux / macOS, from a clone of this repository)
```bash
git clone <repository-url> AdmitCompass
cd AdmitCompass
bash run_review.sh
```
Open http://127.0.0.1:8000. To use another address or port, run for example `HOST=0.0.0.0 PORT=8080 bash run_review.sh`. To pick a Python version, set `PYTHON=python3.12`.

### Manual start (the same settings)
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export PORTKEY_API_KEY="" AC_COPILOT_MODE=mock AC_DB_PATH="$(mktemp -d)/accounts.sqlite3"
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

## Run the tests
```bash
.venv/bin/python -m pytest -q
```
All model calls in the tests are mocked. One live integration test is skipped without a key.

## Where to look
| Route | What |
|---|---|
| `#/` | Homepage with an interactive preview of the saved analysis |
| `#/explore` | 30 MBA programs: details, compare, and official vs. estimated costs |
| `#/dashboard/demo` | Career intelligence dashboard for the saved sample analysis |
| `#/start` | Guided profile (submitting a live analysis needs a key, so it is refused here) |
| `#/signup`, `#/signin` | Accounts (temporary database) |
| **Ask AI** (bottom right) | Copilot in mock mode |

## What's included and excluded
- **Included:**
  - `backend/` and `frontend/` (with fonts);
  - `data/`: evidence store, supplementary research, sources, fixtures, link status;
  - `experiments/`, including the saved demo run that the app reads;
  - `docs/`, `tests/`, `scripts/` and `requirements.txt`.
- **Excluded:**
  - `.env` files, API keys and credentials;
  - existing account databases (`data/app/`);
  - `.venv/`, `.git/` and caches;
  - `data/sources/cache/`: raw copies of third-party web pages, kept only for re-validation and not redistributable. `scripts/build_supplementary.py --offline` needs that cache; a normal run re-fetches the pages.

## Notes
- **Running with a real key:** the normal setup is a `.env` file with `PORTKEY_API_KEY` and the unmodified uvicorn command, without the review exports. This review build intentionally doesn't use one.
- **More documentation:** `README.md` and `docs/` (accounts: `docs/accounts.md`; copilot: `docs/copilot.md`).
