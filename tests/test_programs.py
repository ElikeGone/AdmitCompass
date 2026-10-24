"""Tests for program schemas and the evidence store.

Uses a SYNTHETIC fixture (example.edu URLs) so tests don't depend on the real dataset's contents.
"""
import copy
from datetime import date

import pytest
from pydantic import ValidationError

from backend.app.schemas.claims import Claim
from backend.app.schemas.programs import FACT_NAMES, ProgramDataset, ProgramRecord
from backend.app.tools.evidence_store import EvidenceNotFoundError, EvidenceStore, freshness

UNKNOWN = {"status": "unknown", "unit": "text"}


def unknown_facts():
    return {n: dict(UNKNOWN) for n in FACT_NAMES}


def program(pid="test-a-mba", **facts):
    f = unknown_facts()
    f.update(facts)
    return {"program_id": pid, "university": "Test University", "school": "Test School",
            "program_name": "Full-Time MBA", "degree": "MBA", "facts": f,
            "evidence": [{"evidence_id": f"ev-{pid}-1", "source_id": "src-test-1", "excerpt": "Synthetic excerpt."}]}


SOURCES = [
    {"source_id": "src-test-1", "url": "https://example.edu/a", "title": "Test page", "publisher": "Test U",
     "source_type": "official_university", "accessed": True, "checked_on": "2026-10-23"},
    {"source_id": "src-test-2", "url": "https://example.edu/blocked", "title": "Blocked page", "publisher": "Test U",
     "source_type": "official_university", "accessed": False},
]


def verified(pid, **kw):
    return {"status": "verified", "evidence_ids": [f"ev-{pid}-1"], **kw}


@pytest.fixture
def store():
    a = program("test-a-mba",
                location=verified("test-a-mba", value={"city": "New Haven", "state": "CT"}, unit="location"),
                tuition=verified("test-a-mba", value=80000, unit="USD", period="2026-2027"),
                cost_of_attendance=verified("test-a-mba", value=120000, unit="USD", period="2026-2027"),
                stem_designation=verified("test-a-mba", value={"designated": True, "scope": "MBA", "cip_code": "52.1301"}, unit="stem"),
                employment_rate=verified("test-a-mba", value=90.5, unit="percent", period="Class of 2022",
                                         definition="Accepted offer within 3 months, among those seeking"))
    b = program("test-b-mba",
                location=verified("test-b-mba", value={"city": "Houston", "state": "TX"}, unit="location"),
                cost_of_attendance=verified("test-b-mba", value=95000, unit="USD", period="2026-2027"))
    c = program("test-c-mba")  # everything unknown
    return EvidenceStore(ProgramDataset(schema_version="1.0", programs=[a, b, c], sources=SOURCES))


# --- valid / invalid records ---
def test_valid_record(store):
    assert len(store.list_programs()) == 3


def test_missing_fact_field_rejected():
    p = program()
    del p["facts"]["tuition"]
    with pytest.raises(ValidationError, match="missing fact fields"):
        ProgramRecord(**p)


def test_verified_fact_without_evidence_rejected():
    with pytest.raises(ValidationError, match="evidence_id"):
        ProgramRecord(**program(tuition={"status": "verified", "value": 1, "unit": "USD", "period": "2026-2027"}))


def test_unknown_fact_with_value_rejected():
    with pytest.raises(ValidationError, match="value=None"):
        ProgramRecord(**program(tuition={"status": "unknown", "value": 80000, "unit": "USD"}))


@pytest.mark.parametrize("fact", [
    {"value": -5, "unit": "USD", "period": "2026-2027"},
    {"value": 140, "unit": "percent", "period": "Class of 2025", "definition": "x"},
    {"value": {"city": "X", "state": "Texas"}, "unit": "location"},
])
def test_bad_units_rejected(fact):
    name = {"USD": "tuition", "percent": "employment_rate", "location": "location"}[fact["unit"]]
    with pytest.raises(ValidationError):
        ProgramRecord(**program(**{name: verified("test-a-mba", **fact)}))


# --- missing STEM / unknown sponsorship ---
def test_missing_stem_is_unknown_and_excluded_from_stem_filter(store):
    assert store.get_fact("test-c-mba", "stem_designation").status == "unknown"
    assert store.filter_programs(stem_designated=True) == ["test-a-mba"]
    assert "test-c-mba" in store.filter_programs(stem_designated=True, include_unknown=True)


def test_stem_requires_scope():
    with pytest.raises(ValidationError):
        ProgramRecord(**program(stem_designation=verified("test-a-mba", value={"designated": True}, unit="stem")))


def test_sponsorship_unknown_by_default(store):
    assert all(store.get_fact(p["program_id"], "sponsorship").status == "unknown" for p in store.list_programs())


def test_sponsorship_must_be_employer_specific():
    with pytest.raises(ValidationError):
        ProgramRecord(**program(sponsorship=verified("test-a-mba", value="Many employers sponsor", unit="text")))
    with pytest.raises(ValidationError):
        ProgramRecord(**program(sponsorship=verified("test-a-mba", value={"statement": "sponsors"}, unit="sponsorship")))


# --- evidence linkage ---
def test_fact_with_nonexistent_evidence_id_rejected():
    with pytest.raises(ValidationError, match="unknown evidence ids"):
        ProgramRecord(**program(tuition={"status": "verified", "value": 1, "unit": "USD", "period": "2026-2027",
                                         "evidence_ids": ["ev-does-not-exist"]}))


def test_evidence_with_unknown_source_rejected():
    p = program()
    p["evidence"][0]["source_id"] = "src-missing"
    with pytest.raises(ValidationError, match="unknown source_id"):
        ProgramDataset(schema_version="1.0", programs=[p], sources=SOURCES)


def test_evidence_citing_unaccessed_source_rejected():
    p = program()
    p["evidence"][0]["source_id"] = "src-test-2"
    with pytest.raises(ValidationError, match="not accessed"):
        ProgramDataset(schema_version="1.0", programs=[p], sources=SOURCES)


def test_accessed_source_needs_date():
    s = copy.deepcopy(SOURCES)
    del s[0]["checked_on"]
    with pytest.raises(ValidationError, match="checked_on"):
        ProgramDataset(schema_version="1.0", programs=[], sources=s)


# --- costs & academic years ---
@pytest.mark.parametrize("period", ["2026", "2026-27", "2025-2027", None])
def test_cost_requires_valid_academic_year(period):
    with pytest.raises(ValidationError, match="academic|YYYY"):
        ProgramRecord(**program(tuition=verified("test-a-mba", value=80000, unit="USD", period=period)))


def test_cost_fact_returns_year(store):
    f = store.get_fact("test-a-mba", "cost_of_attendance")
    assert (f.value, f.unit, f.period) == (120000, "USD", "2026-2027")


# --- employment outcome definitions ---
def test_outcome_requires_definition_and_class_year():
    with pytest.raises(ValidationError, match="definition"):
        ProgramRecord(**program(employment_rate=verified("test-a-mba", value=90, unit="percent", period="Class of 2025")))
    with pytest.raises(ValidationError, match="Class of"):
        ProgramRecord(**program(employment_rate=verified("test-a-mba", value=90, unit="percent", period="2025",
                                                         definition="x")))


# --- freshness ---
def test_freshness_flags_old_data():
    old = freshness("Class of 2022", today=date(2026, 10, 23))
    new = freshness("2026-2027", today=date(2026, 10, 23))
    assert old["stale"] is True and "Class of 2022" in old["warning"]
    assert new["stale"] is False and new["warning"] is None
    assert freshness(None)["stale"] is None


def test_get_fact_includes_source_quality(store):
    f = store.get_fact("test-a-mba", "employment_rate")
    assert f.evidence[0]["source_label"] == "Official university source"
    assert f.evidence[0]["source_url"] == "https://example.edu/a"
    assert f.freshness["stale"] is True


# --- retrieval & filtering ---
def test_get_unknown_program_raises(store):
    with pytest.raises(EvidenceNotFoundError):
        store.get_program("nope")


def test_filters(store):
    assert store.filter_programs(max_cost_of_attendance=100000) == ["test-b-mba"]
    assert store.filter_programs(states=["CT"]) == ["test-a-mba"]
    assert store.filter_programs(states=["CT", "TX"], max_cost_of_attendance=200000) == ["test-a-mba", "test-b-mba"]
    assert store.filter_programs() == ["test-a-mba", "test-b-mba", "test-c-mba"]


# --- unsupported verified claims ---
def test_verified_claim_with_real_evidence_id_accepted(store):
    c = Claim(text="Test A MBA is STEM-designated", label="verified_fact", evidence_ids=["ev-test-a-mba-1"])
    store.validate_claim(c)
    assert store.evidence_for_claim(c)[0]["source_url"] == "https://example.edu/a"


def test_verified_claim_with_fake_evidence_id_rejected(store):
    c = Claim(text="Test C sponsors H-1B", label="verified_fact", evidence_ids=["ev-made-up"])
    with pytest.raises(EvidenceNotFoundError):
        store.validate_claim(c)


def test_verified_claim_without_any_evidence_rejected():
    with pytest.raises(ValidationError):
        Claim(text="Test C is STEM-designated", label="verified_fact")


# --- real dataset (skips until built) ---
def test_real_dataset_loads_and_sponsorship_is_never_inferred():
    from backend.app.tools.evidence_store import DATA_DIR
    if not (DATA_DIR / "programs" / "programs.json").exists():
        pytest.skip("real dataset not built yet")
    s = EvidenceStore.load()
    ids = [p["program_id"] for p in s.list_programs()]
    assert {"yale-som-mba", "hbs-mba", "mit-sloan-mba", "chicago-booth-mba", "duke-fuqua-mba", "rice-jones-mba"} <= set(ids)
    for pid in ids:
        sp = s.get_fact(pid, "sponsorship")
        assert sp.status == "unknown" or sp.unit == "sponsorship"
        for name in FACT_NAMES:
            f = s.get_fact(pid, name)
            if f.status == "verified":
                assert f.evidence and all(e["accessed"] for e in f.evidence)
