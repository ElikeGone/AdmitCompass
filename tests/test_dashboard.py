"""Step 10 dashboard: deterministic calculations and that every value traces to the saved run or the evidence store."""
import copy

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.applicant import ApplicantProfile
from backend.app.tools.dashboard import affordability, feasibility, workspace
from backend.app.tools.evidence_store import default_store


@pytest.fixture(scope="module")
def demo():
    return TestClient(app).get("/api/demo").json()


@pytest.fixture(scope="module")
def dash():
    r = TestClient(app).get("/api/dashboard/demo")
    assert r.status_code == 200
    return r.json()


def _profile(demo, **kw):
    return ApplicantProfile.model_validate(demo["profile"]).model_copy(update=kw)


def _rec(demo, pid):
    return copy.deepcopy(next(r for r in demo["report"]["recommendations"] if r["program_id"] == pid))


def _set_coa(rec, value, period="2026-2027"):
    for f in rec["facts"]:
        if f["fact"] == "cost_of_attendance":
            f.update(status="verified", value=value, period=period, evidence_ids=f["evidence_ids"] or ["ev-x"])
    return rec


def test_gap_is_budget_minus_coa(demo, dash):
    store = default_store()
    for p in dash["dashboard"]["programs"]:
        a = p["affordability"]
        f = store.get_fact(p["program_id"], "cost_of_attendance")
        if f.status == "verified":
            assert a["comparable"] and a["gap"] == round(135000 - f.value, 2)
            assert a["cost_of_attendance"]["value"] == f.value
        else:
            assert not a["comparable"] and a["gap"] is None


def test_mit_tuition_only_not_compared(dash):
    mit = next(p for p in dash["dashboard"]["programs"] if p["program_id"] == "mit-sloan-mba")
    a = mit["affordability"]
    assert a["status"] == "no_cost" and a["gap"] is None and a["tuition"]["value"] == 91892


def test_zero_and_negative_gap(demo):
    prof = _profile(demo)
    zero = affordability(prof, _set_coa(_rec(demo, "chicago-booth-mba"), 135000))
    assert zero["gap"] == 0 and zero["status"] == "within" and "no headroom" in zero["reason"]
    neg = affordability(prof, _set_coa(_rec(demo, "chicago-booth-mba"), 150000))
    assert neg["gap"] == -15000 and neg["status"] == "shortfall"


def test_incompatible_periods(demo):
    rec = _rec(demo, "chicago-booth-mba")
    a = affordability(_profile(demo, budget_period="total_program"), rec)
    assert a["status"] == "not_comparable" and a["gap"] is None
    b = affordability(_profile(demo, budget_usd=None), rec)
    assert b["status"] == "no_budget" and b["gap"] is None
    c = affordability(_profile(demo), _set_coa(_rec(demo, "chicago-booth-mba"), 120000, period="per year"))
    assert c["status"] == "no_cost" and c["gap"] is None


def test_unknown_stem_and_sponsorship(demo):
    rec = _rec(demo, "yale-som-mba")
    for f in rec["facts"]:
        if f["fact"] in ("stem_designation", "sponsorship", "international_employment"):
            f.update(status="unknown", value=None, evidence_ids=[])
    fe = feasibility(rec)
    assert fe["stem"]["status"] == "unknown" and fe["stem"]["designated"] is None
    assert fe["sponsorship"] == {"status": "unknown"} and fe["international_outcomes"] is None
    assert any("not evidence that any employer will sponsor" in n for n in fe["notes"])


def test_demo_sponsorship_unknown_stem_verified(dash):
    for p in dash["dashboard"]["programs"]:
        assert p["feasibility"]["sponsorship"]["status"] == "unknown"
        assert p["feasibility"]["stem"]["status"] == "verified"


def test_values_trace_to_saved_run(demo, dash):
    d = dash["dashboard"]
    recs = {r["program_id"]: r for r in demo["report"]["recommendations"]}
    assert [p["program_id"] for p in d["programs"]] == list(recs)
    for p in d["programs"]:
        assert p["fit"]["career_fit"] == recs[p["program_id"]]["career_fit"]
        for c in p["fit"]["supported"]:
            assert all(e in dash["evidence"] for e in c["evidence_ids"])
    gaps = demo["report"]["strategy"]["gaps"]
    assert sorted(g["gap"] for g in d["pathway"]["gaps"]) == sorted(g["gap"] for g in gaps)
    assert all(g["source"].endswith("(AI-inferred)") for g in d["pathway"]["gaps"])


def test_workspace_grouping_and_ids(demo, dash):
    w = dash["dashboard"]["workspace"]
    plan = demo["report"]["strategy"]["weekly_plan"]
    assert len(w["tasks"]) == sum(len(x["actions"]) for x in plan)
    ids = [t["id"] for t in w["tasks"]]
    assert len(set(ids)) == len(ids)
    grouped = [i for ph in w["phases"] for i in ph["task_ids"]]
    assert sorted(grouped) == sorted(ids)  # each task in exactly one phase
    assert workspace(demo["report"])["tasks"] == w["tasks"]  # stable across calls


def test_international_figure_vs_statement(dash):
    io = {p["program_id"]: p["feasibility"]["international_outcomes"] for p in dash["dashboard"]["programs"]}
    assert io["yale-som-mba"]["kind"] == "figure" and io["yale-som-mba"]["period"] == "Class of 2025"
    assert io["chicago-booth-mba"]["kind"] == "statement"  # source says no international statistics exist
    assert io["mit-sloan-mba"] is None and io["duke-fuqua-mba"] is None


def test_deadlines_only_when_verified(dash):
    for p in dash["dashboard"]["programs"]:
        dl = p["deadlines"]
        assert dl["status"] in ("verified", "not_checked", "not_published")
        if dl["status"] == "verified":
            assert dl["cycle"] and (dl.get("evidence") or dl.get("source_url", "").startswith("https://"))


def test_unknown_run_404():
    assert TestClient(app).get("/api/dashboard/nope").status_code == 404
