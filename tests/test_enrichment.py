"""Step 9B: fill-only merging, safe promotion, evidence status, checked vs not-checked, partial STEM, link status."""
import importlib.util
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.schemas.programs import FACT_NAMES, ProgramRecord
from backend.app.tools.catalog import Catalog, evidence_status, load_discovery, stem_is_partial
from backend.app.tools.evidence_store import EvidenceStore

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_dataset", ROOT / "scripts" / "build_dataset.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


@pytest.fixture(scope="module")
def store():
    return EvidenceStore.load()


@pytest.fixture(scope="module")
def catalog(store):
    return Catalog(store, load_discovery())


# ---------- non-overwrite merge ----------
def test_merge_never_overwrites_stronger_evidence():
    primary = {"facts": {"tuition": {"value": 90900, "source_url": "https://a.edu/cost"}, "stem_designation": None}}
    secondary = {"facts": {"tuition": {"value": 1, "source_url": "https://b.edu/x"},
                           "stem_designation": {"value": {"designated": True, "scope": "MBA"}, "source_url": "https://a.edu/stem"}},
                 "urls_checked": [{"url": "https://a.edu/stem", "accessible": True}]}
    out = build.merge_raw(primary, secondary)
    assert out["facts"]["tuition"]["value"] == 90900          # verified primary kept
    assert out["facts"]["stem_designation"]["value"]["designated"] is True  # gap filled
    assert out["_filled_from_secondary"] == ["stem_designation"]
    assert primary["facts"]["stem_designation"] is None        # input not mutated


def test_curated_programs_keep_their_evidence(store):
    # The original six are tier-1 curated; enrichment cannot change their facts.
    booth = store.get_program("chicago-booth-mba")
    assert booth.collection_tier == "curated" and store.get_fact("chicago-booth-mba", "cost_of_attendance").value == 132449


# ---------- safe promotion ----------
def test_programs_without_enough_evidence_are_not_promoted(store):
    audit = json.loads((ROOT / "experiments" / "source_audit.json").read_text(encoding="utf-8"))
    not_promoted = {x["program_id"] for x in audit["not_promoted"]}
    assert {"columbia-cbs-mba", "indiana-kelley-mba"} <= not_promoted
    ids = {p["program_id"] for p in store.list_programs()}
    assert not (ids & not_promoted)
    for p in store.dataset.programs:
        if p.collection_tier == "enriched":
            assert len([n for n, f in p.facts.items() if f.status.value == "verified" and n != "location"]) >= build.MIN_PROMOTE


def test_reviewed_downgrades_are_unknown_with_reason(store):
    for pid, fact in [("cornell-johnson-mba", "stem_designation"), ("berkeley-haas-mba", "cost_of_attendance"),
                      ("minnesota-carlson-mba", "employment_rate"), ("texas-am-mays-mba", "stem_designation")]:
        f = store.get_fact(pid, fact)
        assert f.status == "unknown" and f.note.startswith("Not verified:")


def test_every_promoted_fact_has_accessed_official_source(store):
    for p in store.dataset.programs:
        for name, f in p.facts.items():
            if f.status.value == "verified":
                fv = store.get_fact(p.program_id, name)
                assert fv.evidence and all(e["accessed"] and e["source_type"] == "official_university" for e in fv.evidence)


# ---------- checked vs not checked ----------
def test_checked_flag_distinguishes_not_checked():
    base = {n: {"status": "unknown", "unit": "text"} for n in FACT_NAMES}
    rec = ProgramRecord(program_id="x-mba", university="U", school="S", program_name="MBA", degree="MBA",
                        facts={**base, "tuition": {"status": "unknown", "unit": "USD", "checked": False}})
    assert rec.facts["tuition"].checked is False and rec.facts["location"].checked is True
    with pytest.raises(ValidationError, match="checked"):
        ProgramRecord(program_id="x-mba", university="U", school="S", program_name="MBA", degree="MBA", evidence=[
            {"evidence_id": "ev-x-1", "source_id": "src-x-1", "excerpt": "e"}],
            facts={**base, "test_policy": {"status": "verified", "value": "GMAT", "unit": "text", "evidence_ids": ["ev-x-1"], "checked": False}})


def test_curated_deadlines_marked_not_checked(store):
    f = store.get_program("yale-som-mba").facts["application_deadlines"]
    assert f.status.value == "unknown" and f.checked is False


# ---------- evidence status ----------
def test_evidence_status_rules():
    core = {"tuition", "stem_designation", "test_policy", "employment_rate"}
    assert evidence_status(core | {"location", "duration_months", "application_requirements", "median_base_salary"}) == "detailed"
    assert evidence_status(core) == "partial"  # too few facts
    assert evidence_status({"location", "tuition", "test_policy", "application_requirements", "duration_months",
                            "application_deadlines", "employment_rate", "median_base_salary"}) == "partial"  # no STEM evidence


def test_partial_stem_detection():
    assert stem_is_partial("Management Science major (12 STEM electives) only")
    assert stem_is_partial("Two STEM-designated paths: Financial Mathematics or Management Science")
    assert not stem_is_partial("Entire Daytime MBA program (replacing prior MSTeM track)")
    assert not stem_is_partial("All UNC Kenan-Flagler MBA programs")


def test_catalog_statuses(catalog):
    by = catalog.counts()["by_evidence_status"]
    assert sum(by.values()) == 30 and by["detailed"] >= 5
    items = {i["id"]: i for i in catalog.items}
    assert items["disc-columbia-university-mba"]["evidence_status"] == "unavailable"
    assert items["disc-indiana-university-mba"]["evidence_status"] == "discovered"
    assert items["georgetown-mcdonough-mba"]["stem_partial"] and items["georgetown-mcdonough-mba"]["evidence_status"] == "partial"
    assert items["duke-fuqua-mba"]["stem_partial"] is False


# ---------- links ----------
def test_every_program_has_an_official_link(catalog):
    for it in catalog.items:
        assert it["official_link"] and it["official_link"]["url"].startswith("https://"), it["id"]


def test_blocked_link_is_reported_not_hidden(catalog):
    ross = next(i for i in catalog.items if i["id"] == "michigan-ross-mba")
    assert ross["official_link"]["status"] == "blocked"


def test_detail_endpoint_includes_checked_and_link_status():
    from backend.app.main import app
    d = TestClient(app).get("/api/programs/stanford-gsb-mba").json()
    facts = {f["fact"]: f for f in d["facts"]}
    assert facts["cost_of_attendance"]["value"] == 140940 and facts["cost_of_attendance"]["evidence"][0]["rechecked"]
    assert "status" in facts["cost_of_attendance"]["evidence"][0]["link"]
    assert all("checked" in f for f in d["facts"])
    assert d["item"]["evidence_status"] in ("detailed", "partial")


def test_link_audit_csv_columns():
    import csv
    rows = list(csv.DictReader((ROOT / "experiments" / "link_audit" / "link_audit.csv").open(encoding="utf-8")))
    assert rows and {"status", "checked_at", "original_url", "final_url", "program_id", "issue", "resolution"} <= set(rows[0])
    assert all(r["status"] in ("ok", "redirect_ok", "redirect_offsite", "blocked", "broken", "error", "unreachable") for r in rows)


def test_reason_saying_page_not_fetched_counts_as_not_checked(store):
    assert build.NOT_FETCHED.search("checked: admissions page refers to a separate requirements page that was not fetched")
    assert not build.NOT_FETCHED.search("checked: cost page states tuition only")
    # Wharton's collector said "checked" for STEM but never fetched the relevant page.
    assert store.get_program("wharton-mba").facts["stem_designation"].checked is False
