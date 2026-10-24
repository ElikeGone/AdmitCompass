"""Create (or upgrade in place) the accounts database and purge expired sessions.

    .venv\\Scripts\\python scripts\\init_db.py            # uses AC_DB_PATH or data/app/accounts.sqlite3

The app also creates the tables automatically on first use; this script is for explicit setup and maintenance.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.auth.store import AccountStore  # noqa: E402
from backend.app.core.config import REPO_ROOT  # noqa: E402

path = os.getenv("AC_DB_PATH") or REPO_ROOT / "data" / "app" / "accounts.sqlite3"
store = AccountStore(path)
print(f"Accounts database ready at {path}; purged {store.purge_expired()} expired session(s).")
