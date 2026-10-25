"""Reviewer-only run instrumentation: measured values for one real saved run, plus clearly separated estimates."""
from fastapi.testclient import TestClient

from backend.app.core import usage
from backend.app.main import app
from backend.app.tools.run_record import RUNS_PER_USER_PER_MONTH, cost_block, projections

client = TestClient(app)
FIELDS = ("model", "agent_steps", "tool_calls", "sources", "tokens", "latency_seconds", "estimated_cost",
          "validation_warnings", "safety_checks", "final_recommendation", "projections", "summary")


def test_default_sample_record_has_every_measured_field():
    rec = client.get("/api/demo/record").json()
    for k in FIELDS:
        assert k in rec, k
    # values measured in the saved real Ghana run (report.json totals)
    assert rec["model"] == "gpt-6-luna" and rec["requests"] == 9 and rec["tool_calls"]["count"] == 17
    assert rec["tokens"]["input"] == 54756 and rec["tokens"]["cached_input"] == 26621 and rec["tokens"]["output"] == 8779
    assert rec["latency_seconds"]["wall"] == 53.778
    assert [s["agent"] for s in rec["agent_steps"]] == ["Pathway Matcher", "Evidence Analyst", "Strategy Planner", "Skeptic"]
    assert rec["safety_checks"]["grounding_rules_triggered"] == {"guarantee": 1}
    assert [s["program_id"] for s in rec["final_recommendation"]["shortlist"]] == ["mit-sloan-mba", "yale-som-mba", "duke-fuqua-mba"]


def test_cost_is_not_calculated_without_a_documented_price():
    rec = client.get("/api/demo/record").json()
    assert rec["estimated_cost"] == {"usd": None, "status": "not calculated",
                                     "basis": "not calculated — no documented gpt-6-luna price is configured"}
    assert any(x["label"] == "Estimated cost" and x["value"].startswith("Not calculated") for x in rec["summary"])


def test_projections_are_labeled_estimates_and_scale_linearly():
    rec = client.get("/api/demo/record").json()
    p = rec["projections"]
    assert p["kind"] == "estimate" and "linear" in p["method"]
    runs = [r["runs"] for r in p["rows"]]
    assert runs == [1, RUNS_PER_USER_PER_MONTH, 100 * RUNS_PER_USER_PER_MONTH, 10_000 * RUNS_PER_USER_PER_MONTH] == [1, 4, 400, 40_000]
    for r in p["rows"]:
        assert r["input_tokens"] == 54756 * r["runs"] and r["cached_input_tokens"] == 26621 * r["runs"]
        assert r["output_tokens"] == 8779 * r["runs"] and r["model_requests"] == 9 * r["runs"]
        assert r["estimated_cost_usd"] is None and r["cost_status"] == "not calculated"
    assert any("4 full analyses a month" in a for a in p["assumptions"])
    assert any("saved runs used" in a for a in p["assumptions"])   # measured spread, read from the run reports


def test_cost_formula_when_a_documented_price_exists(monkeypatch):
    monkeypatch.setitem(usage.PRICES_PER_MTOK, "test-model", {"input": 2.0, "cached_input": 0.5, "output": 8.0, "source": "test price"})
    totals = {"input_tokens": 1_000_000, "cached_input_tokens": 400_000, "output_tokens": 100_000, "model_requests": 10}
    # (600,000 × 2 + 400,000 × 0.5 + 100,000 × 8) / 1,000,000 = 1.2 + 0.2 + 0.8 = 2.2
    assert cost_block("test-model", totals) == {"usd": 2.2, "status": "calculated", "basis": "documented price: test price"}
    rows = projections("test-model", totals)["rows"]
    assert [r["estimated_cost_usd"] for r in rows] == [2.2, 8.8, 880.0, 88_000.0]


def test_record_has_no_profile_data_or_keys():
    text = client.get("/api/demo/record").text
    for private in ("140000", "140,000", "Ghana", "profile_id", "citizenship", "PORTKEY", "sk-"):
        assert private not in text, private


def test_india_sample_record_still_available():
    rec = client.get("/api/demo/record?sample=india").json()
    assert rec["tokens"]["input"] == 105041 and rec["projections"]["rows"][1]["input_tokens"] == 4 * 105041
