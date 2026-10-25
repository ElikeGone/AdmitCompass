# Fresh-clone test

The scripts follow README.md exactly: a new folder, a `.env` **one level above** the repo, a virtual environment, `pip install -r requirements.txt`, starting uvicorn, then checking `/health`, `/` and `/api/programs`.
- Any OS (Python): `python scripts/fresh_clone_test.py [--repo-url <git url>]`. This replaces the earlier PowerShell script, which Windows Defender flagged as a false positive ("potentially unwanted software") and removed on checkout, aborting `git clone` (found in the 2026-10-24 grader-workflow test).
- macOS / Linux: `bash scripts/fresh_clone_test.sh [<git url>]`

**Status note:** the project has no git remote yet (no `git init`, per the Step 1 rule), so these runs copy the working tree exactly as a clone would contain it. **Re-run with `-RepoUrl` / the URL argument after pushing to GitHub**; that is the official pre-submission dry run.

The placeholder key used is not a real key. `/health` only reports whether a key was loaded, and no model call is made.

## Results (appended by the scripts)

## 2026-10-24T02:15:49Z - PASS (Windows, PowerShell script)
- Mode: working-tree copy (no git remote yet); Python: Python 3.14.7
- .env one level above the repo; /health ok=True, api_key_configured=True; GET / = 200; GET /api/programs = 200
- Time to installed: 115s; time to app answering /health: 122s (limit: 600s)

## 2026-10-24T02:17:48Z — PASS (MINGW64_NT-10.0-26200, bash script)
- Mode: working-tree copy (no git remote yet); Python: Python 3.11.9
- .env one level above the repo; /health ok=yes, api_key_configured=true; GET / = 200; GET /api/programs = 200
- Time to installed: 93s; time to app answering /health: 103s (limit: 600s)

## 2026-10-25T03:27:59Z - PASS (win32, Python script)
- Mode: git clone of the local repository HEAD; Python 3.14.7
- .env one folder above the repo; /health ok=True, api_key_configured=True; GET / = 200; GET /api/programs = 200
- Time to installed: 57s; time to app answering /health: 60s (limit: 600s)

## 2026-10-25T03:35:42Z - PASS (win32, Python script)
- Mode: git clone of the local repository HEAD; Python 3.14.7
- .env one folder above the repo; /health ok=True, api_key_configured=True; GET / = 200; GET /api/programs = 200
- Time to installed: 62s; time to app answering /health: 66s (limit: 600s)
