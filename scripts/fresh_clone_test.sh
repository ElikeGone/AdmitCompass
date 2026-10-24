#!/usr/bin/env bash
# Fresh-clone test (macOS / Linux; also works in Git Bash on Windows).
#   bash scripts/fresh_clone_test.sh [REPO_URL]
# With REPO_URL: real `git clone`. Without: copies this working tree as a clone would contain it (git-ignored files excluded).
# Then: puts a .env ONE LEVEL ABOVE the repo, follows README.md steps exactly, starts the app, checks /health, records timing.
set -uo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
REPO_URL="${1:-}"
PORT="${PORT:-8765}"
PY="${PYTHON:-python3}"; command -v "$PY" >/dev/null 2>&1 || PY=python
WORK="$(mktemp -d -t acclone-XXXXXX)"
LOG="$SRC/experiments/fresh_clone_test.md"
t0=$(date +%s)
step() { echo "[$(( $(date +%s) - t0 ))s] $*"; }

step "work dir: $WORK"
if [ -n "$REPO_URL" ]; then
  step "git clone $REPO_URL"; git clone --depth 1 "$REPO_URL" "$WORK/repo" || { echo "clone failed"; exit 1; }; MODE="git clone of $REPO_URL"
else
  step "no repo URL: copying working tree as a clone (excluding git-ignored paths)"
  mkdir -p "$WORK/repo"
  tar -C "$SRC" --exclude=./.venv --exclude=./.git --exclude='*/__pycache__' --exclude=./.pytest_cache --exclude=./data/app \
      --exclude=./data/sponsorship/raw --exclude=./data/sources/cache --exclude=./.env --exclude='./.env.*' --exclude=./logs \
      --exclude=./experiments/outputs -cf - . | tar -C "$WORK/repo" -xf -
  cp "$SRC/.env.example" "$WORK/repo/.env.example"
  MODE="working-tree copy (no git remote yet)"
fi
# A placeholder key (not a real key): /health only reports whether a key was loaded; no model call is made.
printf 'PORTKEY_API_KEY=fresh-clone-placeholder-not-a-real-key\n' > "$WORK/.env"
step ".env placed one level ABOVE the repo: $WORK/.env"

cd "$WORK/repo" || exit 1
step "README step: python -m venv .venv"; "$PY" -m venv .venv || exit 1
VPY=".venv/bin/python"; [ -x "$VPY" ] || VPY=".venv/Scripts/python"
step "README step: pip install -r requirements.txt"; "$VPY" -m pip install -q -r requirements.txt || exit 1
t_install=$(( $(date +%s) - t0 ))
step "README step: start uvicorn on port $PORT"
"$VPY" -m uvicorn backend.app.main:app --host 127.0.0.1 --port "$PORT" > "$WORK/server.log" 2>&1 &
SERVER=$!
ok=""; for i in $(seq 1 60); do
  H=$(curl -s "http://127.0.0.1:$PORT/health" || true)
  if echo "$H" | grep -q '"status":"ok"'; then ok=1; break; fi; sleep 1
done
t_ready=$(( $(date +%s) - t0 ))
KEY=$(echo "$H" | grep -o '"api_key_configured":[a-z]*' | cut -d: -f2)
HOME_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/")
PROG_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/api/programs")
kill "$SERVER" 2>/dev/null; wait "$SERVER" 2>/dev/null
RESULT=$([ -n "$ok" ] && [ "$KEY" = "true" ] && [ "$HOME_CODE" = 200 ] && [ "$PROG_CODE" = 200 ] && echo PASS || echo FAIL)
step "health=$( [ -n "$ok" ] && echo ok || echo FAIL ) api_key_configured=$KEY home=$HOME_CODE programs=$PROG_CODE -> $RESULT"
{
  echo ""
  echo "## $(date -u +%Y-%m-%dT%H:%M:%SZ) — $RESULT ($(uname -s 2>/dev/null || echo unknown), bash script)"
  echo "- Mode: $MODE; Python: $("$VPY" --version 2>&1)"
  echo "- .env one level above the repo; /health ok=$( [ -n "$ok" ] && echo yes || echo no ), api_key_configured=$KEY; GET / = $HOME_CODE; GET /api/programs = $PROG_CODE"
  echo "- Time to installed: ${t_install}s; time to app answering /health: ${t_ready}s (limit: 600s)"
} >> "$LOG"
rm -rf "$WORK"
[ "$RESULT" = PASS ]
