"""Regression: the public API never exposes raw validation/exception text (schema internals, paths, model output).
The raw detail stays in the saved developer run record and the server log."""
import json
import logging

from fastapi.testclient import TestClient

from backend.app.core.public_errors import public_error, public_event, public_report
from backend.app.main import SAMPLES, app

RAW_MARKERS = ["validation error for", "validation errors for", "type=value_error", "errors.pydantic.dev", "input_value=",
               "PathwayOutput", "Traceback", "File \"", "C:\\\\", "/Users/", "/home/", "PORTKEY_API_KEY", "sk-"]
SAFE_KEYS = {"status", "message", "error_code"}


def _errors(obj):
    """Yield every value stored under an "error" key, anywhere in the payload."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "error" and v is not None:
                yield v
            yield from _errors(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _errors(v)


def test_demo_payload_has_no_raw_validation_details():
    body = TestClient(app).get("/api/demo?sample=india")   # the India run has a failed format check
    assert body.status_code == 200
    text = body.text
    for m in RAW_MARKERS:
        assert m not in text, f"raw detail leaked: {m!r}"
    errs = list(_errors(body.json()))
    assert errs, "the saved demo has a failed format check; its event should carry a structured error"
    for e in errs:
        assert isinstance(e, dict) and set(e) <= SAFE_KEYS | {"reason"}, e
    assert {"status": "retryable_error", "message": "The analysis could not be validated. Please retry.",
            "error_code": "OUTPUT_VALIDATION_FAILED"} in errs


def test_dashboard_payload_has_no_raw_validation_details():
    text = TestClient(app).get("/api/dashboard/demo").text
    for m in RAW_MARKERS:
        assert m not in text, m


def test_raw_detail_is_kept_in_the_developer_run_record():
    trace = json.loads((SAMPLES["india"]["dir"] / "trace.json").read_text(encoding="utf-8"))
    raw = [e["detail"]["error"] for e in trace if e.get("kind") == "validation" and e["detail"].get("error")]
    assert raw and "validation error" in raw[0]


def test_failure_and_tool_errors_are_replaced():
    raw = ('1 validation error for StrategyOutput\nclaims.0\n  Value error [type=value_error, input_value={"text": "x"}] '
           'File "C:\\Users\\me\\app.py", line 3')
    e = public_event({"seq": 1, "kind": "agent_failure", "agent": "orchestrator", "detail": {"error": raw}})
    assert e["detail"]["error"]["error_code"] == "OUTPUT_VALIDATION_FAILED"
    t = public_event({"seq": 2, "kind": "tool_call", "agent": "evidence_analyst",
                      "detail": {"tool": "get_evidence", "ok": False, "error": "evidence id ev-x not in /srv/data/store.json"}})
    assert t["detail"]["error"]["error_code"] == "TOOL_LOOKUP_FAILED" and "/srv" not in json.dumps(t)
    assert public_error("ReadTimeout: timed out", "failure")["error_code"] == "UPSTREAM_UNAVAILABLE"
    assert public_error("KeyError: 'x' at /opt/app", "failure") == {"status": "failed", "error_code": "ANALYSIS_FAILED",
                                                                    "message": "The analysis stopped safely before finishing."}


def test_budget_reason_kept_only_when_it_is_a_known_template():
    ok = public_report({"status": "stopped_budget", "error": "request limit reached (25/25)"})["error"]
    assert ok["error_code"] == "BUDGET_LIMIT_REACHED" and ok["reason"] == "request limit reached (25/25)"
    odd = public_report({"status": "stopped_budget", "error": "limit hit; prompt was: SYSTEM ..."})["error"]
    assert "reason" not in odd
    ev = public_event({"seq": 3, "kind": "budget_stop", "agent": "orchestrator", "detail": {"reason": "see C:\\secrets"}})
    assert ev["detail"]["reason"] == "usage limit reached"


def test_public_helpers_do_not_mutate_the_server_side_trace():
    original = {"seq": 1, "kind": "validation", "agent": "skeptic", "detail": {"ok": False, "error": "1 validation error for X"}}
    public_event(original)
    assert original["detail"]["error"] == "1 validation error for X"


def test_validation_failure_is_logged_server_side(caplog):
    from backend.app.agents import runner
    with caplog.at_level(logging.WARNING, logger="admitcompass.errors"):
        runner.errlog.warning("%s output failed validation (attempt %s): %s", "skeptic", 1, "1 validation error for X")
    assert "1 validation error for X" in caplog.text


def test_profile_input_errors_are_guidance_only():
    c = TestClient(app)
    leaks = ["ApplicantProfile", "type=", "input_value", "input_type", "errors.pydantic.dev", "Traceback", "File \"",
             "C:\\\\", "/Users/", "'abc'", "not-a-dict", "-3"]
    for profile in ({"years_experience": -3, "budget_usd": "abc"}, "not-a-dict"):
        r = c.post("/api/runs", json={"profile": profile, "confirm_paid_run": True})
        assert r.status_code == 422
        for m in leaks:
            assert m not in r.text, (m, r.text)
        d = r.json()["detail"]
        assert set(d) == {"message", "fields"} and all(isinstance(v, str) for v in d["fields"].values())
    r = c.post("/api/runs", json={"profile": {"budget_usd": "abc"}, "confirm_paid_run": True})
    assert "budget_usd" in r.json()["detail"]["fields"]
