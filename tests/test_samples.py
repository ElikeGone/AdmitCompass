"""Saved samples: Ghana consulting is the default everywhere; the India sample stays available."""
from fastapi.testclient import TestClient

from backend.app.main import DEFAULT_SAMPLE, app

c = TestClient(app)


def test_default_sample_is_ghana():
    assert DEFAULT_SAMPLE == "ghana"
    d = c.get("/api/demo").json()
    assert d["sample"]["key"] == "ghana" and d["profile"]["citizenship_country"] == "Ghana"
    assert d["run_folder"].endswith("fixture-audit-consulting-ghana")
    assert c.get("/api/dashboard/demo").json()["sample"]["key"] == "ghana"


def test_india_sample_still_available():
    d = c.get("/api/dashboard/demo-india").json()
    assert d["sample"]["key"] == "india" and d["profile"]["citizenship_country"] == "India"
    assert c.get("/api/demo?sample=india").json()["sample"]["others"][0]["route"] == "demo"
    assert c.get("/api/demo/record?sample=india").status_code == 200


def test_unknown_sample_is_404():
    assert c.get("/api/dashboard/demo-nowhere").status_code == 404
    assert c.get("/api/demo?sample=nowhere").status_code == 404


def test_ghana_shortlist_has_scoped_employer_filing_history():
    d = c.get("/api/dashboard/demo").json()["dashboard"]
    for pg in d["programs"]:
        h = pg["feasibility"]["h1b_history"]
        assert h["status"] == "ok" and h["occupation"] == "management_consulting" and h["metro"] == "Boston"
        top = [e for e in h["employers"] if e["total_filings"] > 0]
        assert top and h["data_source"]["fiscal_year"] == 2025 and "Not a guarantee" in h["note"]


def test_copilot_accepts_either_sample_as_context(monkeypatch):
    """The 'Ask AI about my pathway' entry sends the sample being viewed; the scripted model is the only 'call'."""
    import json
    from backend.app.copilot import routes as cp_routes
    from backend.app.core.llm import ChatResult
    seen = []
    def fake(messages, *a, **k):
        seen.append(json.loads(messages[1]["content"]))
        return ChatResult(content=json.dumps({"answer": "Start with the diagnostics.", "citations": [], "uncertainties": [],
                                              "answer_type": "general", "next_step": None}))
    app.state.copilot_chat_factory = lambda: fake
    cp_routes.limiter.reset()
    monkeypatch.setenv("PORTKEY_API_KEY", "test-not-a-real-key")
    client = TestClient(app, headers={"Origin": "http://testserver"})
    try:
        for i, (run, country_budget) in enumerate([("demo", 140000), ("demo-india", 135000)]):
            r = client.post("/api/copilot/chat", json={"conversation_id": f"samples-ctx-{i:04d}", "message": "What should I do next on my pathway?",
                                                       "context": {"run": run}})
            assert r.status_code == 200
            assert seen[-1]["SAVED_ANALYSIS"]["applicant_profile"]["budget_usd"] == country_budget
        assert client.post("/api/copilot/chat", json={"conversation_id": "samples-ctx-9999", "message": "hi",
                                                      "context": {"run": "demo-mars"}}).status_code == 422
    finally:
        app.state.copilot_chat_factory = None
