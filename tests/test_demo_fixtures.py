"""Task 2: demo fixtures, detailed-only demo shortlist, and the international layer only for profiles needing work authorization."""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.applicant import ApplicantProfile
from backend.app.tools.catalog import detailed_program_ids, store_for_profile
from backend.app.tools.dashboard import build_dashboard
from backend.app.tools.evidence_store import default_store

FIX = Path(__file__).resolve().parents[1] / "data" / "fixtures"


def load(name):
    return ApplicantProfile.model_validate_json((FIX / name).read_text(encoding="utf-8"))


def test_new_fixtures_match_the_brief():
    g, d = load("applicant_audit_consulting_ghana.json"), load("applicant_domestic_tech_us.json")
    assert g.profile_id == "fixture-audit-consulting-ghana" and g.is_fictional and g.citizenship_country == "Ghana"
    assert g.needs_us_work_authorization is True and g.education[0].field == "Accounting" and g.years_work_experience == 5
    assert "audit" in g.current_function.lower() and g.target_function == "Management consulting" and g.long_term_location == "Boston"
    assert d.profile_id == "fixture-domestic-tech-us" and d.is_fictional and d.citizenship_country == "United States"
    assert d.needs_us_work_authorization is False and "Engineering" in d.education[0].field
    assert d.target_function == "Product management" and d.long_term_location == "Seattle"
    keys = TestClient(app).get("/api/fixtures").json()
    assert {"audit-consulting-ghana", "domestic-tech-us"} <= set(keys)


def test_demo_runs_use_only_detailed_programs():
    store = default_store()
    detailed = detailed_program_ids(store)
    assert detailed and len(detailed) < len(store.list_programs())
    demo = store_for_profile(store, load("applicant_audit_consulting_ghana.json"))
    assert sorted(p["program_id"] for p in demo.list_programs()) == sorted(detailed)
    real = load("applicant_domestic_tech_us.json").model_copy(update={"is_fictional": False})
    assert len(store_for_profile(store, real).list_programs()) == len(store.list_programs())   # real users: full store


def test_international_layer_only_when_work_authorization_needed():
    store = default_store()
    report = TestClient(app).get("/api/demo").json()["report"]
    gh = build_dashboard(store, load("applicant_audit_consulting_ghana.json"), report)
    us = build_dashboard(store, load("applicant_domestic_tech_us.json"), report)
    assert gh["international_layer"] is True and all(p["feasibility"] for p in gh["programs"])
    assert us["international_layer"] is False and all(p["feasibility"] is None for p in us["programs"])
    # the Ghana profile's sponsorship evidence is scoped to its target occupation and city
    h = gh["programs"][1]["feasibility"]["h1b_history"]
    assert h["occupation"] == "management_consulting" and h["metro"] == "Boston"


def test_sponsorship_scope_differs_between_profiles():
    g, d = load("applicant_audit_consulting_ghana.json"), load("applicant_domestic_tech_us.json")
    from backend.app.tools.sponsorship import metro_for, occupation_for
    assert (occupation_for(g.target_function), metro_for(g.long_term_location)) == ("management_consulting", "Boston")
    assert (occupation_for(d.target_function), metro_for(d.long_term_location)) == ("product_management", "Seattle")
