"""AdmitCompass FastAPI app: JSON API + static single-page frontend.

Routes
  GET  /health                       safe status (no secrets)
  GET  /api/config                   limits shown in the UI (read-only)
  GET  /api/fixtures                 the two fictional demo applicant profiles
  GET  /api/demo                     the saved, real fictional tech-PM run (no model call)
  POST /api/runs                     start ONE live paid analysis (requires confirm_paid_run=true)
  GET  /api/runs/{run_id}            status + events since `since` + result when finished
Model, prompts, budgets, and evidence data are server-side only and cannot be set by requests.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from .core.budget import RunBudget
from .core.config import AUTHORIZED_MODEL, MissingAPIKeyError, REPO_ROOT, load_environment
from .orchestrator import MAX_REVISIONS
from .runs import RunManager, RunRejected, max_live_runs
from .schemas.applicant import ApplicantProfile
from .tools.catalog import Catalog, load_discovery
from .tools.evidence_store import EvidenceNotFoundError, EvidenceStore, default_store

load_environment()

FRONTEND_DIR = REPO_ROOT / "frontend"
FIXTURES_DIR = REPO_ROOT / "data" / "fixtures"
DEMO_RUN_DIR = REPO_ROOT / "experiments" / "agent_runs" / "20261023T180104Z_fixture-tech-pm-india"
FIXTURE_FILES = {"tech-pm": "applicant_tech_pm.json", "energy-finance": "applicant_energy_finance.json",
                 "audit-consulting-ghana": "applicant_audit_consulting_ghana.json", "domestic-tech-us": "applicant_domestic_tech_us.json"}


def default_chat_factory():
    from .core.llm import make_portkey_responses_chat
    return make_portkey_responses_chat()


app = FastAPI(title="AdmitCompass", version="0.6.0")
from fastapi.middleware.gzip import GZipMiddleware  # noqa: E402

app.add_middleware(GZipMiddleware, minimum_size=1000)  # smaller transfers over slow links and tunnels
app.state.runs = RunManager(chat_factory=lambda: app.state.chat_factory(), store_factory=EvidenceStore.load)
app.state.chat_factory = default_chat_factory


# ---------- helpers ----------
def evidence_map(store: EvidenceStore, report: dict) -> dict[str, dict]:
    """Resolve every evidence id in a report to its source (deterministic, from the store)."""
    ids: set[str] = set()
    for rec in report.get("recommendations", []):
        for f in rec.get("facts", []):
            ids.update(f.get("evidence_ids", []))
        for c in rec.get("analyst_claims", []):
            ids.update(c.get("evidence_ids", []))
    strat = report.get("strategy") or {}
    ids.update((strat.get("test_guidance") or {}).get("evidence_ids", []))
    out = {}
    for i in sorted(ids):
        try:
            ev = store.get_evidence(i)
            pid, fact = store.fact_for_evidence(i)
            f = store.get_fact(pid, fact)
            out[i] = {**ev, "fact": fact, "data_period": f.period, "freshness": f.freshness}
        except EvidenceNotFoundError:
            out[i] = {"evidence_id": i, "missing": True}
    return out


def public_events(trace: list) -> list[dict]:
    """Trace events are metadata only (no prompts, no model reasoning); pass them through as dicts."""
    return [e.model_dump(mode="json") if hasattr(e, "model_dump") else e for e in trace]


def result_payload(mode: str, profile: dict, report: dict, trace: list, extra: dict | None = None) -> dict:
    return {"mode": mode, "profile": profile, "report": report, "events": public_events(trace),
            "evidence": evidence_map(default_store(), report), **(extra or {})}


# ---------- routes ----------
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": AUTHORIZED_MODEL,
            "api_key_configured": bool(os.getenv("PORTKEY_API_KEY", "").strip())}


def _accounts_enabled() -> bool:
    from .auth.routes import accounts_enabled
    return accounts_enabled()


@app.get("/api/config")
def config() -> dict:
    b = RunBudget()
    mgr: RunManager = app.state.runs
    return {"model": AUTHORIZED_MODEL, "max_requests": b.max_requests, "max_total_tokens": b.max_total_tokens,
            "max_tool_calls": b.max_tool_calls, "max_seconds": b.max_seconds, "max_revisions": MAX_REVISIONS,
            "live_runs_allowed": max_live_runs(), "live_runs_used": mgr.live_runs_started,
            "live_run_active": mgr.active().run_id if mgr.active() else None,
            "api_key_configured": bool(os.getenv("PORTKEY_API_KEY", "").strip()),
            "price_known": False, "accounts_enabled": _accounts_enabled()}


@app.get("/api/fixtures")
def fixtures() -> dict:
    out = {}
    for key, fname in FIXTURE_FILES.items():
        prof = ApplicantProfile.model_validate_json((FIXTURES_DIR / fname).read_text(encoding="utf-8"))
        out[key] = {"profile": prof.model_dump(mode="json"), "has_saved_run": key == "tech-pm"}
    return out


@app.get("/api/demo")
def demo() -> dict:
    if not (DEMO_RUN_DIR / "report.json").exists():
        raise HTTPException(404, "Saved demo run not found.")
    load = lambda n: json.loads((DEMO_RUN_DIR / n).read_text(encoding="utf-8"))  # noqa: E731
    verification = load("verification.json") if (DEMO_RUN_DIR / "verification.json").exists() else None
    profile = ApplicantProfile.model_validate(load("input_profile.json")).model_dump(mode="json")  # normalize legacy fields
    return result_payload("saved_demo", profile, load("report.json"), load("trace.json"),
                          {"run_folder": DEMO_RUN_DIR.name, "verification": verification})


_catalog: Catalog | None = None


def catalog() -> Catalog:
    global _catalog
    if _catalog is None:
        _catalog = Catalog(default_store(), load_discovery())
    return _catalog


@app.get("/api/programs")
def programs(q: str = Query("", max_length=80), tier: str | None = Query(None, pattern="^(verified|discovered)$"),
             state: str | None = Query(None, pattern="^[A-Z]{2}$"), stem_verified: bool = False,
             max_cost: float | None = Query(None, gt=0, le=1_000_000),
             sort: str = Query("relevance", pattern="^(relevance|name|cost|state|evidence)$"),
             status: str | None = Query(None, pattern="^(detailed|partial|discovered|unavailable)$")) -> dict:
    cat = catalog()
    items = cat.search(q=q, tier=tier, state=state, stem_verified=stem_verified, max_cost=max_cost, sort=sort, status=status)
    d = cat.discovery
    return {"items": items, "total": len(items), "counts": cat.counts(),
            "states": sorted({i["state"] for i in cat.items if i["state"]}),
            "index": {"built_on": d.built_on.isoformat() if d else None, "is_live_search": False,
                      "method": d.method if d else None, "sources_note": d.sources_note if d else None}}


@app.get("/api/programs/{item_id}")
def program_detail(item_id: str) -> dict:
    """Verified programs: every fact with its evidence. Discovered programs: the record only (no facts exist)."""
    it = catalog().get(item_id)
    if it is None:
        raise HTTPException(404, "Unknown program id.")
    from .tools.supplementary import research_view
    if it["tier"] != "verified":
        return {"item": it, "facts": None, "research": research_view(item_id)}
    store = default_store()
    from .schemas.programs import FACT_NAMES
    facts = []
    for name in FACT_NAMES:
        f = store.get_fact(item_id, name)
        raw = store.get_program(item_id).facts[name]
        links = catalog().links
        facts.append({"fact": name, "status": f.status, "value": f.value, "period": f.period, "definition": f.definition,
                      "note": f.note[:300], "checked": raw.checked, "freshness_warning": f.freshness.get("warning"),
                      "evidence": [{**e, "link": links.get(e["source_url"], {})} for e in f.evidence]})
    from .tools.sponsorship import get_sponsorship_evidence
    return {"item": it, "facts": facts, "research": research_view(item_id), "h1b_history": get_sponsorship_evidence(item_id)}


@app.get("/api/dashboard/{run_id}")
def dashboard(run_id: str) -> dict:
    """Career Intelligence dashboard for the saved demo ('demo') or a finished live run. Deterministic, no model calls."""
    from .tools.dashboard import build_dashboard
    if run_id == "demo":
        base = demo()
    else:
        try:
            state = app.state.runs.get(run_id)
        except RunRejected as e:
            raise HTTPException(e.status_code, e.message)
        if state.report is None:
            raise HTTPException(409, "This analysis hasn't finished yet.")
        base = result_payload("live", state.profile.model_dump(mode="json"), state.report.model_dump(mode="json"),
                              state.orchestrator.trace if state.orchestrator else [])
    profile = ApplicantProfile.model_validate(base["profile"])
    return {"mode": base["mode"], "profile": base["profile"], "evidence": base["evidence"],
            "dashboard": build_dashboard(default_store(), profile, base["report"])}


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")  # no model/prompt/budget overrides possible
    profile: dict[str, Any]
    confirm_paid_run: bool = False


@app.post("/api/runs", status_code=202)
def start_run(req: RunRequest) -> dict:
    if not req.confirm_paid_run:
        raise HTTPException(400, "Live analysis uses the paid course API. Set confirm_paid_run=true to proceed.")
    data = {k: v for k, v in req.profile.items() if k != "profile_id"}
    data.setdefault("is_fictional", False)
    data["profile_id"] = f"session-{uuid.uuid4().hex[:8]}"   # server-generated
    try:
        profile = ApplicantProfile.model_validate(data)
    except Exception as e:
        raise HTTPException(422, f"Invalid profile: {str(e)[:400]}")
    try:
        state = app.state.runs.start(profile)
    except RunRejected as e:
        raise HTTPException(e.status_code, e.message)
    except MissingAPIKeyError:
        raise HTTPException(503, "The server has no PORTKEY_API_KEY configured. Add it to .env (see README).")
    return {"run_id": state.run_id, "status": state.status}


@app.get("/api/runs/{run_id}")
def run_status(run_id: str, since: int = Query(0, ge=0)) -> dict:
    try:
        state = app.state.runs.get(run_id)
    except RunRejected as e:
        raise HTTPException(e.status_code, e.message)
    trace = state.orchestrator.trace if state.orchestrator else []
    out = {"run_id": run_id, "status": state.status, "error": state.error,
           "events": public_events(trace[since:]), "next_since": len(trace),
           "elapsed_seconds": round(((state.finished_at or time.time()) - state.created_at), 1),
           "budget": state.orchestrator.budget.snapshot() if state.orchestrator else None}
    if state.status != "running" and state.report is not None:
        report = state.report.model_dump(mode="json")
        out["result"] = result_payload("live", state.profile.model_dump(mode="json"), report, trace)
    return out


@app.exception_handler(Exception)
def unhandled(_, exc: Exception):  # never leak internals or secrets
    return JSONResponse(status_code=500, content={"detail": "Internal error. Check the server log."})


# ---------- accounts ----------
from .auth.routes import router as auth_router  # noqa: E402

app.include_router(auth_router)
from .copilot.routes import router as copilot_router  # noqa: E402

app.include_router(copilot_router)


# ---------- frontend ----------
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")
