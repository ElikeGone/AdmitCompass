# Fresh-clone test

The scripts follow README.md exactly: a new folder, a `.env` **one level above** the repo, a virtual environment, `pip install -r requirements.txt`, starting uvicorn, then checking `/health`, `/` and `/api/programs`.
- Windows: `powershell -ExecutionPolicy Bypass -File scripts\fresh_clone_test.ps1 [-RepoUrl <git url>]`
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
