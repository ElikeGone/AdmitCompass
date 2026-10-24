"""Auth + account API.

POST /api/auth/signup  {name, email, password, password_confirm}  -> creates account, starts a session
POST /api/auth/login   {email, password}                          -> starts a session (rate-limited)
POST /api/auth/logout                                             -> deletes the session, clears the cookie
GET  /api/auth/me                                                 -> {user, csrf_token} or {user: null}
GET/POST/DELETE /api/account/saved[/{program_id}]                 -> saved programs
GET/PUT /api/account/progress/{run_id}                            -> completed roadmap task ids
GET/PUT /api/account/profile                                      -> applicant profile (validated ApplicantProfile)
POST /api/account/import                                          -> opt-in merge of browser-local data (adds only)

Security: the session token lives only in an HttpOnly, SameSite=Lax cookie (Secure on HTTPS); the DB stores its
SHA-256. Every state-changing request must come from this site's Origin; signed-in writes also need the per-session
CSRF token in the X-CSRF-Token header. Passwords, hashes and tokens are never logged or returned.
"""
from __future__ import annotations

import hmac
import os
import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..schemas.applicant import ApplicantProfile
from .security import DUMMY_HASH, LoginLimiter, hash_password, new_token, token_hash, verify_password
from .store import SESSION_TTL_S, AccountStore

COOKIE = "ac_session"
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
TASK_RE = re.compile(r"^w\d{1,3}-\d{1,3}$")
RUN_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
PASSWORD_MIN, PASSWORD_MAX = 10, 128

def accounts_enabled() -> bool:
    """Accounts are ON by default; set AC_ENABLE_ACCOUNTS=false/0/no/off to turn them off. Read per request so tests can toggle it."""
    return os.getenv("AC_ENABLE_ACCOUNTS", "true").strip().lower() not in ("0", "false", "no", "off")


def _require_enabled() -> None:
    if not accounts_enabled():
        raise HTTPException(404, "Accounts are turned off on this server.")


router = APIRouter(dependencies=[Depends(_require_enabled)])
limiter = LoginLimiter()


def get_store(request: Request) -> AccountStore:
    st = getattr(request.app.state, "accounts", None)
    if st is None:
        from ..core.config import REPO_ROOT
        st = request.app.state.accounts = AccountStore(os.getenv("AC_DB_PATH") or REPO_ROOT / "data" / "app" / "accounts.sqlite3")
    return st


# ---------- CSRF / origin ----------
def _allowed_origins(request: Request) -> set[str]:
    own = f"{request.url.scheme}://{request.headers.get('host', '')}"
    extra = {o.strip().rstrip("/") for o in os.getenv("AC_ALLOWED_ORIGINS", "").split(",") if o.strip()}
    return {own} | extra


def require_same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin is None:
        ref = request.headers.get("referer")
        m = re.match(r"^(https?://[^/]+)", ref or "")
        origin = m.group(1) if m else None
    if origin is None or origin.rstrip("/") not in _allowed_origins(request):
        raise HTTPException(403, "Request blocked: it didn't come from this site.")


def _cookie_secure(request: Request) -> bool:
    return request.url.scheme == "https" or os.getenv("AC_COOKIE_SECURE") == "1"


def _set_cookie(resp: Response, request: Request, token: str) -> None:
    resp.set_cookie(COOKIE, token, max_age=SESSION_TTL_S, httponly=True, samesite="lax", secure=_cookie_secure(request), path="/")


def _clear_cookie(resp: Response, request: Request) -> None:
    resp.delete_cookie(COOKIE, path="/", httponly=True, samesite="lax", secure=_cookie_secure(request))


# ---------- session helpers ----------
def current_session(request: Request, store: Annotated[AccountStore, Depends(get_store)]):
    tok = request.cookies.get(COOKIE)
    return store.get_session(token_hash(tok)) if tok else None


def require_user(request: Request, store: Annotated[AccountStore, Depends(get_store)]) -> int:
    s = current_session(request, store)
    if s is None:
        raise HTTPException(401, "Please sign in.")
    if request.method not in ("GET", "HEAD"):
        require_same_origin(request)
        sent = request.headers.get("x-csrf-token", "")
        if not hmac.compare_digest(sent, s["csrf_token"]):
            raise HTTPException(403, "Request blocked: missing or invalid security token. Refresh the page and try again.")
    return s["user_id"]


def _start_session(request: Request, resp: Response, store: AccountStore, uid: int) -> dict:
    old = request.cookies.get(COOKIE)
    if old:
        store.delete_session(token_hash(old))  # rotate: never reuse a pre-login session id
    tok, csrf = new_token(), new_token()
    store.create_session(token_hash(tok), uid, csrf)
    _set_cookie(resp, request, tok)
    u = store.user_by_id(uid)
    return {"user": {"name": u["name"], "email": u["email"]}, "csrf_token": csrf}


def _ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# ---------- auth ----------
class SignupIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(max_length=200)
    email: str = Field(max_length=254)
    password: str = Field(max_length=1000)
    password_confirm: str = Field(max_length=1000)


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=254)
    password: str = Field(max_length=1000)


@router.post("/api/auth/signup", status_code=201)
def signup(body: SignupIn, request: Request, response: Response, store: Annotated[AccountStore, Depends(get_store)]):
    require_same_origin(request)
    name, email = " ".join(body.name.split()), body.email.strip().lower()
    errors = {}
    if not 1 <= len(name) <= 80:
        errors["name"] = "Enter your name (up to 80 characters)."
    if not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address."
    if not PASSWORD_MIN <= len(body.password) <= PASSWORD_MAX:
        errors["password"] = f"Use {PASSWORD_MIN} to {PASSWORD_MAX} characters."
    elif body.password.strip() == "" or body.password.lower() == email:
        errors["password"] = "Choose a password that isn't blank or your email."
    if body.password != body.password_confirm:
        errors["password_confirm"] = "Passwords don't match."
    if errors:
        raise HTTPException(422, {"message": "Please fix the highlighted fields.", "fields": errors})
    uid = store.create_user(email, name, hash_password(body.password))
    if uid is None:
        raise HTTPException(409, {"message": "An account with this email already exists. Try signing in.", "fields": {"email": "Already registered."}})
    return _start_session(request, response, store, uid)


@router.post("/api/auth/login")
def login(body: LoginIn, request: Request, response: Response, store: Annotated[AccountStore, Depends(get_store)]):
    require_same_origin(request)
    email, ip = body.email.strip().lower(), _ip(request)
    if limiter.blocked(email, ip):
        raise HTTPException(429, "Too many failed sign-in attempts. Please wait 15 minutes and try again.")
    u = store.user_by_email(email)
    ok = verify_password(body.password, u["password_hash"] if u else DUMMY_HASH) and u is not None
    if not ok:
        limiter.fail(email, ip)
        raise HTTPException(401, "Email or password is incorrect.")
    limiter.succeed(email)
    return _start_session(request, response, store, u["id"])


@router.post("/api/auth/logout")
def logout(request: Request, response: Response, store: Annotated[AccountStore, Depends(get_store)]):
    require_same_origin(request)
    tok = request.cookies.get(COOKIE)
    if tok:
        store.delete_session(token_hash(tok))
    _clear_cookie(response, request)
    return {"ok": True}


@router.get("/api/auth/me")
def me(request: Request, response: Response, store: Annotated[AccountStore, Depends(get_store)]):
    response.headers["Cache-Control"] = "no-store"
    s = current_session(request, store)
    if s is None:
        if request.cookies.get(COOKIE):
            _clear_cookie(response, request)  # expired or revoked
        return {"user": None}
    u = store.user_by_id(s["user_id"])
    return {"user": {"name": u["name"], "email": u["email"]}, "csrf_token": s["csrf_token"]}


# ---------- account-owned data (every query is scoped to the signed-in user's id) ----------
def _valid_program(pid: str) -> bool:
    from ..main import catalog
    return bool(re.match(r"^[a-z0-9-]{1,80}$", pid)) and catalog().get(pid) is not None


@router.get("/api/account/saved")
def saved(uid: Annotated[int, Depends(require_user)], store: Annotated[AccountStore, Depends(get_store)]):
    return {"program_ids": store.saved(uid)}


@router.post("/api/account/saved/{program_id}")
def save_program(program_id: str, uid: Annotated[int, Depends(require_user)], store: Annotated[AccountStore, Depends(get_store)]):
    if not _valid_program(program_id):
        raise HTTPException(404, "Unknown program.")
    store.add_saved(uid, program_id)
    return {"program_ids": store.saved(uid)}


@router.delete("/api/account/saved/{program_id}")
def unsave_program(program_id: str, uid: Annotated[int, Depends(require_user)], store: Annotated[AccountStore, Depends(get_store)]):
    store.remove_saved(uid, program_id)
    return {"program_ids": store.saved(uid)}


class ProgressIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    done: list[str] = Field(max_length=500)


def _check_run(run_id: str) -> None:
    if not RUN_RE.match(run_id):
        raise HTTPException(422, "Invalid analysis id.")


@router.get("/api/account/progress/{run_id}")
def get_progress(run_id: str, uid: Annotated[int, Depends(require_user)], store: Annotated[AccountStore, Depends(get_store)]):
    _check_run(run_id)
    return {"done": store.progress(uid, run_id)}


@router.put("/api/account/progress/{run_id}")
def put_progress(run_id: str, body: ProgressIn, uid: Annotated[int, Depends(require_user)], store: Annotated[AccountStore, Depends(get_store)]):
    _check_run(run_id)
    ids = sorted(set(body.done))
    if any(not TASK_RE.match(t) for t in ids):
        raise HTTPException(422, "Invalid task id.")
    store.set_progress(uid, run_id, ids)
    return {"done": store.progress(uid, run_id)}


@router.get("/api/account/profile")
def get_profile(uid: Annotated[int, Depends(require_user)], store: Annotated[AccountStore, Depends(get_store)]):
    return {"profile": store.profile(uid)}


@router.put("/api/account/profile")
def put_profile(body: dict, uid: Annotated[int, Depends(require_user)], store: Annotated[AccountStore, Depends(get_store)]):
    try:
        p = ApplicantProfile.model_validate({**body, "profile_id": "account-profile", "is_fictional": False})
    except ValidationError as e:
        raise HTTPException(422, {"message": "The profile has invalid fields.", "fields": {".".join(map(str, x["loc"])): x["msg"] for x in e.errors()[:10]}})
    store.save_profile(uid, p.model_dump(mode="json"))
    return {"profile": store.profile(uid)}


class ImportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    saved: list[str] = Field(default_factory=list, max_length=200)
    progress: dict[str, list[str]] = Field(default_factory=dict)


@router.post("/api/account/import")
def import_local(body: ImportIn, uid: Annotated[int, Depends(require_user)], store: Annotated[AccountStore, Depends(get_store)]):
    """Adds browser-local items to the account. Never deletes or overwrites; invalid and duplicate items are counted, not stored."""
    out = {"saved_added": 0, "saved_duplicates": 0, "saved_invalid": 0, "tasks_added": 0, "tasks_duplicates": 0, "tasks_invalid": 0}
    for pid in dict.fromkeys(body.saved):
        if not _valid_program(pid):
            out["saved_invalid"] += 1
        elif store.add_saved(uid, pid):
            out["saved_added"] += 1
        else:
            out["saved_duplicates"] += 1
    if len(body.progress) > 20:
        raise HTTPException(422, "Too many analyses in one import.")
    for run_id, ids in body.progress.items():
        if not RUN_RE.match(run_id) or len(ids) > 500:
            out["tasks_invalid"] += len(ids) if isinstance(ids, list) else 1
            continue
        good = [t for t in dict.fromkeys(ids) if TASK_RE.match(t)]
        out["tasks_invalid"] += len(ids) - len(good) - (len(ids) - len(dict.fromkeys(ids)))
        added = store.add_progress(uid, run_id, good)
        out["tasks_added"] += added
        out["tasks_duplicates"] += len(good) - added
    return out
