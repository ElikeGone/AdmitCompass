"""Step 11: accounts, sessions, CSRF, rate limiting, isolation and import. Uses a temporary SQLite file per test."""
import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

from backend.app.auth import routes
from backend.app.auth.store import AccountStore
from backend.app.main import app

ORIGIN = {"Origin": "http://testserver"}
PW = "correct horse battery"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("AC_ENABLE_ACCOUNTS", "true")   # accounts are off by default (Task 5); these tests turn them on
    app.state.accounts = AccountStore(tmp_path / "accounts.sqlite3")
    routes.limiter.reset()
    yield tmp_path / "accounts.sqlite3"
    app.state.accounts = None
    routes.limiter.reset()


def client():
    return TestClient(app, headers=ORIGIN)


def signup(c, email="ana@example.com", name="Ana", pw=PW):
    return c.post("/api/auth/signup", json={"name": name, "email": email, "password": pw, "password_confirm": pw})


def csrf(c):
    return {"X-CSRF-Token": c.get("/api/auth/me").json()["csrf_token"]}


def test_signup_creates_session_and_me(db):
    c = client()
    r = signup(c, email="  Ana@Example.COM ")
    assert r.status_code == 201 and r.json()["user"] == {"name": "Ana", "email": "ana@example.com"}
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "ac_session=" in cookie
    assert c.get("/api/auth/me").json()["user"]["email"] == "ana@example.com"  # persists (like a refresh)


def test_signup_validation_and_duplicates(db):
    c = client()
    bad = c.post("/api/auth/signup", json={"name": "", "email": "nope", "password": "short", "password_confirm": "other"})
    assert bad.status_code == 422 and set(bad.json()["detail"]["fields"]) == {"name", "email", "password", "password_confirm"}
    assert signup(c).status_code == 201
    dup = signup(client(), email="ANA@example.com")
    assert dup.status_code == 409


def test_password_not_stored_in_plaintext(db):
    signup(client())
    raw = db.read_bytes()
    assert PW.encode() not in raw
    row = sqlite3.connect(db).execute("SELECT password_hash FROM users").fetchone()[0]
    assert row.startswith("scrypt$") and PW not in row


def test_session_token_only_hashed_in_db(db):
    c = client(); signup(c)
    tok = c.cookies.get("ac_session")
    stored = sqlite3.connect(db).execute("SELECT token_hash FROM sessions").fetchone()[0]
    assert tok and tok != stored and tok not in db.read_bytes().decode("latin-1")


def test_login_logout_and_invalid_credentials(db):
    signup(client())
    c = client()
    assert c.post("/api/auth/login", json={"email": "ana@example.com", "password": "wrong password!"}).status_code == 401
    assert c.post("/api/auth/login", json={"email": "nobody@example.com", "password": PW}).status_code == 401
    r = c.post("/api/auth/login", json={"email": "ANA@example.com", "password": PW})
    assert r.status_code == 200 and r.json()["user"]["name"] == "Ana"
    old = c.cookies.get("ac_session")
    assert c.post("/api/auth/logout").status_code == 200
    assert c.get("/api/auth/me").json()["user"] is None
    # the old token no longer works even if replayed
    c2 = TestClient(app, headers=ORIGIN, cookies={"ac_session": old})
    assert c2.get("/api/auth/me").json()["user"] is None


def test_session_rotates_on_login(db):
    c = client(); signup(c)
    first = c.cookies.get("ac_session")
    c.post("/api/auth/login", json={"email": "ana@example.com", "password": PW})
    second = c.cookies.get("ac_session")
    assert first != second
    assert TestClient(app, cookies={"ac_session": first}).get("/api/auth/me").json()["user"] is None


def test_expired_session_fails(db):
    c = client(); signup(c)
    con = sqlite3.connect(db); con.execute("UPDATE sessions SET expires_at = ?", (time.time() - 1,)); con.commit(); con.close()
    assert c.get("/api/auth/me").json()["user"] is None
    assert c.get("/api/account/saved").status_code == 401


def test_idle_session_fails(db):
    c = client(); signup(c)
    con = sqlite3.connect(db); con.execute("UPDATE sessions SET last_seen = ?", (time.time() - 2 * 24 * 3600,)); con.commit(); con.close()
    assert c.get("/api/auth/me").json()["user"] is None


def test_rate_limiting(db):
    signup(client())
    c = client()
    for _ in range(5):
        assert c.post("/api/auth/login", json={"email": "ana@example.com", "password": "bad password 1"}).status_code == 401
    blocked = c.post("/api/auth/login", json={"email": "ana@example.com", "password": PW})
    assert blocked.status_code == 429  # even the right password is refused while blocked


def test_csrf_origin_required(db):
    no_origin = TestClient(app)
    assert no_origin.post("/api/auth/signup", json={"name": "A", "email": "a@example.com", "password": PW, "password_confirm": PW}).status_code == 403
    evil = TestClient(app, headers={"Origin": "https://evil.example"})
    assert evil.post("/api/auth/login", json={"email": "a@example.com", "password": PW}).status_code == 403


def test_csrf_token_required_for_account_writes(db):
    c = client(); signup(c)
    assert c.post("/api/account/saved/yale-som-mba").status_code == 403  # no token
    assert c.post("/api/account/saved/yale-som-mba", headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert c.post("/api/account/saved/yale-som-mba", headers=csrf(c)).status_code == 200
    cross = TestClient(app, headers={"Origin": "https://evil.example"}, cookies={"ac_session": c.cookies.get("ac_session")})
    assert cross.post("/api/account/saved/mit-sloan-mba", headers=csrf(c)).status_code == 403


def test_account_data_isolated(db):
    a, b = client(), client()
    signup(a, "a@example.com", "A"); signup(b, "b@example.com", "B")
    a.post("/api/account/saved/yale-som-mba", headers=csrf(a))
    a.put("/api/account/progress/ae6f197e0040", json={"done": ["w1-0", "w1-1"]}, headers=csrf(a))
    assert b.get("/api/account/saved").json()["program_ids"] == []
    assert b.get("/api/account/progress/ae6f197e0040").json()["done"] == []
    assert b.get("/api/account/profile").json()["profile"] is None
    # B removing A's program id only touches B's rows
    b.delete("/api/account/saved/yale-som-mba", headers=csrf(b))
    assert a.get("/api/account/saved").json()["program_ids"] == ["yale-som-mba"]
    # A's CSRF token doesn't authorize B's session
    assert b.post("/api/account/saved/mit-sloan-mba", headers=csrf(a)).status_code == 403


def test_guest_access_and_account_endpoints_need_login(db):
    g = client()
    assert g.get("/api/programs").status_code == 200 and g.get("/api/dashboard/demo").status_code == 200
    assert g.get("/api/account/saved").status_code == 401


def test_saved_validation_and_progress(db):
    c = client(); signup(c); h = csrf(c)
    assert c.post("/api/account/saved/not-a-real-program", headers=h).status_code == 404
    assert c.put("/api/account/progress/ae6f197e0040", json={"done": ["drop table"]}, headers=h).status_code == 422
    r = c.put("/api/account/progress/ae6f197e0040", json={"done": ["w2-0", "w1-0", "w1-0"]}, headers=h)
    assert r.json()["done"] == ["w1-0", "w2-0"]


def test_profile_roundtrip_and_screening(db):
    c = client(); signup(c); h = csrf(c)
    ok = c.put("/api/account/profile", json={"citizenship_country": "India", "years_work_experience": 5, "target_function": "Product management"}, headers=h)
    assert ok.status_code == 200 and ok.json()["profile"]["years_work_experience"] == 5
    bad = c.put("/api/account/profile", json={"passport_number": "X1234567"}, headers=h)
    assert bad.status_code == 422


def test_import_is_additive_and_safe(db):
    c = client(); signup(c); h = csrf(c)
    c.post("/api/account/saved/yale-som-mba", headers=h)
    c.put("/api/account/progress/ae6f197e0040", json={"done": ["w1-0"]}, headers=h)
    r = c.post("/api/account/import", headers=h, json={"saved": ["yale-som-mba", "mit-sloan-mba", "bogus-program"],
                                                        "progress": {"ae6f197e0040": ["w1-0", "w1-1", "evil"]}})
    assert r.status_code == 200
    assert r.json() == {"saved_added": 1, "saved_duplicates": 1, "saved_invalid": 1, "tasks_added": 1, "tasks_duplicates": 1, "tasks_invalid": 1}
    assert c.get("/api/account/saved").json()["program_ids"] == ["yale-som-mba", "mit-sloan-mba"]
    assert c.get("/api/account/progress/ae6f197e0040").json()["done"] == ["w1-0", "w1-1"]
    assert client().post("/api/account/import", json={"saved": []}).status_code == 401


def test_accounts_are_off_by_default(monkeypatch):
    monkeypatch.delenv("AC_ENABLE_ACCOUNTS", raising=False)
    c = client()
    assert c.get("/api/config").json()["accounts_enabled"] is False
    assert c.get("/api/auth/me").status_code == 404
    assert c.post("/api/auth/signup", json={"name": "A", "email": "a@example.com", "password": PW, "password_confirm": PW}).status_code == 404
    monkeypatch.setenv("AC_ENABLE_ACCOUNTS", "true")
    assert c.get("/api/config").json()["accounts_enabled"] is True and c.get("/api/auth/me").status_code == 200
