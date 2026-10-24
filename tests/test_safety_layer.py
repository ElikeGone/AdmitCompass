"""Evidence + safety layer and the run record (developer/report view)."""
import json

import pytest
from fastapi.testclient import TestClient

from backend.app.copilot import routes as cp_routes
from backend.app.core.safety import REFUSAL_TEXT, sensitive_request
from backend.app.main import app
from backend.app.tools.evidence_rows import evidence_rows
from backend.app.tools.evidence_store import default_store
from backend.app.tools.safety_demo import run_safety_demo

client = TestClient(app, headers={"Origin": "http://testserver"})


@pytest.mark.parametrize("q,kind", [
    ("What are my chances of getting into MIT Sloan?", "admission_odds"),
    ("Will I get into Booth with a 700?", "admission_odds"),
    ("How likely am I to be admitted to Yale?", "admission_odds"),
    ("What are my odds of a scholarship at Duke?", "admission_odds"),
    ("Am I eligible for STEM OPT?", "immigration_advice"),
    ("Can I get an H-1B after graduating from Duke?", "immigration_advice"),
    ("Can I stay in the US after graduation?", "immigration_advice"),
    ("Will McKinsey sponsor me?", None),          # answered with employer filing history + "not a guarantee"
    ("What is MIT Sloan tuition?", None),
    ("Which schools accept the GRE?", None),
    ("Does Duke have good odds of placing in consulting?", None),
])
def test_sensitive_request_classifier(q, kind):
    assert sensitive_request(q) == kind


def test_copilot_refuses_odds_and_immigration_before_any_model_call(monkeypatch):
    def must_not_be_called(*a, **k):
        raise AssertionError("the model must not be called")
    app.state.copilot_chat_factory = lambda: must_not_be_called
    cp_routes.limiter.reset()
    monkeypatch.setenv("PORTKEY_API_KEY", "test-not-a-real-key")
    try:
        for i, (q, kind) in enumerate([("What are my chances of getting into MIT Sloan?", "admission_odds"),
                                       ("Am I eligible for STEM OPT after Duke?", "immigration_advice")]):
            j = client.post("/api/copilot/chat", json={"conversation_id": f"safety-layer-{i:04d}", "message": q}).json()
            assert j["answer_type"] == "refused" and j["answer"] == REFUSAL_TEXT[kind]
    finally:
        app.state.copilot_chat_factory = None


def test_safety_test_mode_stops_every_unsafe_input():
    r = client.get("/api/safety/demo").json()
    assert r["total"] == 5 and r["stopped"] == 5
    assert [s["id"] for s in r["scenarios"]] == ["D1", "D2", "D3", "D4", "D5"]
    d5 = r["scenarios"][4]
    assert "$50,000" in d5["input"] and "$91,892" in d5["shown_to_user"]   # the verified figure replaces the conflicting one


def test_safety_demo_is_deterministic():
    store = default_store()
    assert run_safety_demo(store) == run_safety_demo(store)


def test_evidence_rows_have_status_source_date_period_and_tradeoff():
    rows = {r["fact"]: r for r in evidence_rows(default_store(), "mit-sloan-mba")}
    assert rows["cost_of_attendance"]["status"] == "estimated"            # MIT publishes no official total
    assert "Poets&Quants" in rows["cost_of_attendance"]["claim"]
    assert rows["tuition"]["status"] == "verified" and "$91,892" in rows["tuition"]["claim"]
    assert rows["international_employment"]["status"] == "unknown" and rows["international_employment"]["source_url"] is None
    for r in rows.values():
        assert r["status"] in {"verified", "source-backed paraphrase", "estimated", "unknown"} and r["tradeoff"]
        if r["status"] != "unknown":
            assert r["source_url"].startswith("https://") and r["checked_on"]


def test_paraphrased_official_fact_is_labeled_as_paraphrase():
    rows = {r["fact"]: r for r in evidence_rows(default_store(), "duke-fuqua-mba")}
    assert rows["cost_of_attendance"]["status"] == "source-backed paraphrase"


def test_dashboard_carries_evidence_rows():
    d = client.get("/api/dashboard/demo").json()["dashboard"]
    assert all(pg["evidence_rows"] for pg in d["programs"])


def test_run_record_has_the_report_fields_and_no_private_data():
    r = client.get("/api/demo/record")
    assert r.status_code == 200
    rec = r.json()
    for k in ("model", "agent_steps", "tool_calls", "sources", "tokens", "latency_seconds", "estimated_cost",
              "validation_warnings", "safety_checks", "final_recommendation", "summary"):
        assert k in rec, k
    assert rec["model"] == "gpt-6-luna" and rec["tokens"]["input"] == 105041 and rec["tokens"]["cached_input"] == 64600
    assert rec["tool_calls"]["count"] == 24 and len(rec["agent_steps"]) == 4 and rec["sources"]["source_ids"]
    assert rec["estimated_cost"]["usd"] is None and "no documented" in rec["estimated_cost"]["basis"]   # never invented
    text = r.text
    for private in ("135000", "135,000", "India", "profile_id", "PORTKEY", "sk-"):
        assert private not in text, private
    assert all(v == "[from profile]" for c in rec["tool_calls"]["calls"] if c["tool"] == "search_programs" for v in c["args"].values())


def test_live_record_for_unknown_run_is_404():
    assert client.get("/api/runs/doesnotexist/record").status_code == 404
