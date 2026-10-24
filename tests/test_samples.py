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
