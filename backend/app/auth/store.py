"""SQLite data-access layer for accounts. Every query is parameterized; every account-owned query filters by user_id."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,               -- stored lower-cased
  name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,              -- sha256 of the cookie token; the token itself is never stored
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  csrf_token TEXT NOT NULL,
  created_at REAL NOT NULL,
  expires_at REAL NOT NULL,
  last_seen REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);
CREATE TABLE IF NOT EXISTS saved_programs (
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  program_id TEXT NOT NULL,
  created_at REAL NOT NULL,
  PRIMARY KEY (user_id, program_id)
);
CREATE TABLE IF NOT EXISTS task_progress (
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  run_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  PRIMARY KEY (user_id, run_id, task_id)
);
CREATE TABLE IF NOT EXISTS profiles (
  user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  profile_json TEXT NOT NULL,               -- a validated ApplicantProfile (no names/contact details by design)
  updated_at REAL NOT NULL
);
"""

SESSION_TTL_S = 7 * 24 * 3600     # absolute lifetime
SESSION_IDLE_S = 24 * 3600        # expires after a day without use


class AccountStore:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(SCHEMA)

    def _q(self, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, args).fetchall()

    def _x(self, sql: str, args: tuple = ()) -> int:
        with self._lock:
            return self._conn.execute(sql, args).rowcount  # rows actually changed (0 for INSERT OR IGNORE duplicates)

    # ---- users ----
    def create_user(self, email: str, name: str, password_hash: str) -> int | None:
        try:
            with self._lock:
                return self._conn.execute("INSERT INTO users (email, name, password_hash, created_at) VALUES (?, ?, ?, ?)",
                                          (email, name, password_hash, time.time())).lastrowid
        except sqlite3.IntegrityError:
            return None

    def user_by_email(self, email: str) -> sqlite3.Row | None:
        r = self._q("SELECT * FROM users WHERE email = ?", (email,))
        return r[0] if r else None

    def user_by_id(self, uid: int) -> sqlite3.Row | None:
        r = self._q("SELECT id, email, name, created_at FROM users WHERE id = ?", (uid,))
        return r[0] if r else None

    # ---- sessions ----
    def create_session(self, token_hash: str, user_id: int, csrf: str) -> None:
        now = time.time()
        self._x("INSERT INTO sessions (token_hash, user_id, csrf_token, created_at, expires_at, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
                (token_hash, user_id, csrf, now, now + SESSION_TTL_S, now))

    def get_session(self, token_hash: str) -> sqlite3.Row | None:
        r = self._q("SELECT * FROM sessions WHERE token_hash = ?", (token_hash,))
        if not r:
            return None
        s, now = r[0], time.time()
        if now > s["expires_at"] or now - s["last_seen"] > SESSION_IDLE_S:
            self.delete_session(token_hash)
            return None
        self._x("UPDATE sessions SET last_seen = ? WHERE token_hash = ?", (now, token_hash))
        return s

    def delete_session(self, token_hash: str) -> None:
        self._x("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    def purge_expired(self) -> int:
        now = time.time()
        return self._x("DELETE FROM sessions WHERE expires_at < ? OR last_seen < ?", (now, now - SESSION_IDLE_S))

    # ---- saved programs ----
    def saved(self, uid: int) -> list[str]:
        return [r["program_id"] for r in self._q("SELECT program_id FROM saved_programs WHERE user_id = ? ORDER BY created_at", (uid,))]

    def add_saved(self, uid: int, pid: str) -> bool:
        return self._x("INSERT OR IGNORE INTO saved_programs (user_id, program_id, created_at) VALUES (?, ?, ?)", (uid, pid, time.time())) > 0

    def remove_saved(self, uid: int, pid: str) -> None:
        self._x("DELETE FROM saved_programs WHERE user_id = ? AND program_id = ?", (uid, pid))

    # ---- task progress ----
    def progress(self, uid: int, run_id: str) -> list[str]:
        return [r["task_id"] for r in self._q("SELECT task_id FROM task_progress WHERE user_id = ? AND run_id = ? ORDER BY task_id", (uid, run_id))]

    def set_progress(self, uid: int, run_id: str, task_ids: list[str]) -> None:
        with self._lock:
            c = self._conn
            c.execute("BEGIN")
            try:
                c.execute("DELETE FROM task_progress WHERE user_id = ? AND run_id = ?", (uid, run_id))
                c.executemany("INSERT INTO task_progress (user_id, run_id, task_id) VALUES (?, ?, ?)", [(uid, run_id, t) for t in task_ids])
                c.execute("COMMIT")
            except Exception:
                c.execute("ROLLBACK")
                raise

    def add_progress(self, uid: int, run_id: str, task_ids: list[str]) -> int:
        n = 0
        for t in task_ids:
            n += self._x("INSERT OR IGNORE INTO task_progress (user_id, run_id, task_id) VALUES (?, ?, ?)", (uid, run_id, t))
        return n

    # ---- profile ----
    def profile(self, uid: int) -> dict | None:
        r = self._q("SELECT profile_json FROM profiles WHERE user_id = ?", (uid,))
        return json.loads(r[0]["profile_json"]) if r else None

    def save_profile(self, uid: int, profile: dict) -> None:
        self._x("INSERT INTO profiles (user_id, profile_json, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET profile_json = excluded.profile_json, updated_at = excluded.updated_at",
                (uid, json.dumps(profile), time.time()))
