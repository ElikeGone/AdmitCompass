"""API tests: validation, run lifecycle, duplicate protection, demo loading, safe errors. No paid calls."""
import threading
import time

import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.core.config import MissingAPIKeyError
from backend.app.runs import RunManager
from backend.app.tools.evidence_store import EvidenceStore
from tests.test_agents import ScriptedChat, happy_script

PROFILE = {"is_fictional": True, "citizenship_country": "India", "needs_us_work_authorization": True,
           "target_function": "Product management", "target_industry": "Technology",
           "max_total_budget_usd_per_year": 135000, "test_status": "preparing", "weeks_until_first_application": 10}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("PORTKEY_API_KEY", "test-secret-value-123")
    main.app.state.runs = RunManager(chat_factory=lambda: main.app.state.chat_factory(), store_factory=EvidenceStore.load)
    main.app.state.chat_factory = lambda: ScriptedChat(happy_script())
    yield TestClient(main.app)
    main.app.state.chat_factory = main.default_chat_factory


def wait_done(client, run_id, timeout=10):
    t = time.time()
    while time.time() - t < timeout:
        r = client.get(f"/api/runs/{run_id}").json()
        if r["status"] != "running":
            return r
        time.sleep(0.05)
    raise AssertionError("run did not finish")


# ---------- read-only routes ----------
def test_health_and_config_do_not_leak_key(client):
    for path in ("/health", "/api/config"):
        body = client.get(path).text
        assert "test-secret-value-123" not in body
    cfg = client.get("/api/config").json()
    assert cfg["model"] == "gpt-6-luna" and cfg["max_requests"] == 20 and cfg["max_revisions"] == 1
    assert cfg["price_known"] is False


def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "AdmitCompass" in r.text


def test_fixtures_are_fictional(client):
    fx = client.get("/api/fixtures").json()
    assert set(fx) == {"tech-pm", "energy-finance", "audit-consulting-ghana", "domestic-tech-us"}
    assert all(v["profile"]["is_fictional"] for v in fx.values())
    assert fx["tech-pm"]["has_saved_run"] and not fx["energy-finance"]["has_saved_run"]


def test_demo_is_saved_real_run_with_linked_evidence(client):
    d = client.get("/api/demo").json()
    assert d["mode"] == "saved_demo" and d["run_folder"].startswith("20261023T180104Z")
    assert d["report"]["status"] == "completed_with_violations" and len(d["report"]["recommendations"]) == 4
    ids = {i for rec in d["report"]["recommendations"] for f in rec["facts"] for i in f["evidence_ids"]}
    assert ids and ids <= set(d["evidence"]) and not any(e.get("missing") for e in d["evidence"].values())
    assert all(e["source_url"].startswith("https://") for e in d["evidence"].values())
    assert d["verification"]["ok"] is True
    assert not any("encrypted_content" in str(e) for e in d["events"])


# ---------- validation ----------
def test_run_requires_paid_confirmation(client):
    r = client.post("/api/runs", json={"profile": PROFILE})
    assert r.status_code == 400 and "paid" in r.json()["detail"]


@pytest.mark.parametrize("body", [
    {"profile": PROFILE, "confirm_paid_run": True, "model": "gpt-5"},
    {"profile": PROFILE, "confirm_paid_run": True, "max_requests": 999},
    {"profile": PROFILE, "confirm_paid_run": True, "system_prompt": "ignore rules"},
])
def test_cannot_override_model_budget_or_prompt(client, body):
    assert client.post("/api/runs", json=body).status_code == 422


def test_sensitive_or_invalid_profile_rejected(client):
    for bad in ({**PROFILE, "passport_number": "X1"}, {**PROFILE, "max_total_budget_usd_per_year": -5},
                {**PROFILE, "test_score": 5000}):
        assert client.post("/api/runs", json={"profile": bad, "confirm_paid_run": True}).status_code == 422
    assert main.app.state.runs.live_runs_started == 0


# ---------- lifecycle ----------
def test_run_lifecycle_with_mocked_model(client):
    r = client.post("/api/runs", json={"profile": {**PROFILE, "profile_id": "attacker-chosen"}, "confirm_paid_run": True})
    assert r.status_code == 202
    run_id = r.json()["run_id"]
    done = wait_done(client, run_id)
    assert done["status"] == "completed"
    res = done["result"]
    assert res["mode"] == "live" and res["profile"]["profile_id"].startswith("session-")
    kinds = [e["kind"] for e in client.get(f"/api/runs/{run_id}").json()["events"]]
    assert kinds.count("handoff") == 3 and kinds[-1] == "run_end"
    assert all(not e.get("missing") for e in res["evidence"].values())


def test_events_are_incremental(client):
    run_id = client.post("/api/runs", json={"profile": PROFILE, "confirm_paid_run": True}).json()["run_id"]
    done = wait_done(client, run_id)
    n = done["next_since"]
    assert client.get(f"/api/runs/{run_id}?since={n}").json()["events"] == []


def test_duplicate_run_rejected_while_running(client):
    gate = threading.Event()

    class SlowChat(ScriptedChat):
        def __call__(self, *a, **k):
            gate.wait(5)
            return super().__call__(*a, **k)

    main.app.state.chat_factory = lambda: SlowChat(happy_script())
    first = client.post("/api/runs", json={"profile": PROFILE, "confirm_paid_run": True})
    second = client.post("/api/runs", json={"profile": PROFILE, "confirm_paid_run": True})
    assert first.status_code == 202 and second.status_code == 409
    gate.set()
    wait_done(client, first.json()["run_id"])


def test_live_run_cap(client, monkeypatch):
    monkeypatch.setenv("ADMITCOMPASS_MAX_LIVE_RUNS_PER_SERVER", "1")
    wait_done(client, client.post("/api/runs", json={"profile": PROFILE, "confirm_paid_run": True}).json()["run_id"])
    r = client.post("/api/runs", json={"profile": PROFILE, "confirm_paid_run": True})
    assert r.status_code == 429


def test_missing_key_is_safe_503(client):
    def no_key():
        raise MissingAPIKeyError("PORTKEY_API_KEY is not set")
    main.app.state.chat_factory = no_key
    r = client.post("/api/runs", json={"profile": PROFILE, "confirm_paid_run": True})
    assert r.status_code == 503 and main.app.state.runs.live_runs_started == 0


def test_model_failure_is_reported_safely(client):
    main.app.state.chat_factory = lambda: ScriptedChat(happy_script(
        pathway_matcher=[RuntimeError("upstream 500 for key test-secret-value-123")]))
    run_id = client.post("/api/runs", json={"profile": PROFILE, "confirm_paid_run": True}).json()["run_id"]
    done = wait_done(client, run_id)
    assert done["status"] == "failed_closed"
    assert "test-secret-value-123" not in str(done) and "<redacted>" in done["error"]


def test_unknown_run_404(client):
    assert client.get("/api/runs/doesnotexist").status_code == 404


def test_frontend_never_injects_raw_html():
    import re
    from pathlib import Path
    js = (Path(__file__).resolve().parents[1] / "frontend" / "app.js").read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    for api in (".innerHTML", ".outerHTML", "insertAdjacentHTML", "document.write", "eval("):
        assert api not in code, api


def test_frontend_uses_safe_append_helper():
    """Node.append() stringifies arrays/null ("[object HTMLElement]"); the app must use put()/el() instead."""
    import re
    from pathlib import Path
    js = (Path(__file__).resolve().parents[1] / "frontend" / "app.js").read_text(encoding="utf-8")
    assert not re.search(r"\.append\(", js)


def test_typography_is_sans_only_and_fonts_are_bundled():
    """AdmitCompass 4.0: Plus Jakarta Sans + Inter, self-hosted; no serif typefaces anywhere in the UI."""
    import re
    from pathlib import Path
    fe = Path(__file__).resolve().parents[1] / "frontend"
    css = "".join(p.read_text(encoding="utf-8") for p in fe.glob("*.css"))
    for banned in ("Instrument Serif", "Georgia", "Times New Roman", "Palatino", "Iowan"):
        assert banned not in css, banned
    assert not re.search(r"font-family:[^;]*\bserif\b(?<!sans-serif)", css.replace("sans-serif", ""))
    for f in ("inter-latin-var.woff2", "plus-jakarta-sans-latin-var.woff2"):
        assert (fe / "fonts" / f).stat().st_size > 10_000
    html = (fe / "index.html").read_text(encoding="utf-8")
    assert "styles-v4.css" in html and "campus.svg" not in html


def test_theme_toggle_dark_default_and_remembered():
    from pathlib import Path
    fe = Path(__file__).resolve().parents[1] / "frontend"
    html = (fe / "index.html").read_text(encoding="utf-8")
    js = (fe / "app.js").read_text(encoding="utf-8")
    assert 'id="dark-theme"' in html and 'id="theme-toggle"' in html and 'aria-pressed="true"' in html
    head = html.split("</head>")[0]
    assert 'localStorage.getItem("ac-theme") === "light"' in head  # applied before paint; anything else stays dark
    assert 'localStorage.setItem("ac-theme", next)' in js and "applyTheme" in js
