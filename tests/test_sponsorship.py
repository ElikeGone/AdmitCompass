"""Task 1: H-1B LCA employer evidence — filter rules, alias matching, the join, the agent tool, and guarantee blocking."""
import csv
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.agents.grounding import check_claim, risky_language
from backend.app.main import app
from backend.app.schemas.claims import Claim
from backend.app.tools import sponsorship as sp
from backend.app.tools.agent_tools import ToolBox
from backend.app.tools.evidence_store import default_store

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_sponsorship as bsp  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data" / "sponsorship"


def row(**kw):
    base = {"DECISION_DATE": None, "CASE_STATUS": "Certified", "VISA_CLASS": "H-1B", "JOB_TITLE": "Consultant", "SOC_CODE": "13-1111.00",
            "SOC_TITLE": "Management Analysts", "EMPLOYER_NAME": "McKinsey & Company, Inc. United States", "WORKSITE_CITY": "Boston",
            "WORKSITE_STATE": "MA", "WAGE_RATE_OF_PAY_FROM": 190000, "WAGE_UNIT_OF_PAY": "Year", "TOTAL_WORKER_POSITIONS": 1}
    base.update(kw)
    return base


# ---------- filter ----------
def test_filter_keeps_only_certified_h1b_target_occupations_and_cities():
    assert bsp.keep(row()) == ("management_consulting", "Boston")
    assert bsp.keep(row(CASE_STATUS="Certified - Withdrawn")) is None
    assert bsp.keep(row(CASE_STATUS="Denied")) is None
    assert bsp.keep(row(VISA_CLASS="E-3 Australian")) is None
    assert bsp.keep(row(WORKSITE_CITY="Cambridge")) is None                       # Boston means the city of Boston
    assert bsp.keep(row(WORKSITE_CITY="Boston", WORKSITE_STATE="VA")) is None       # state must match too
    assert bsp.keep(row(WORKSITE_CITY="Brooklyn", WORKSITE_STATE="NY")) is None     # NYC = Manhattan only (stated assumption)
    assert bsp.keep(row(WORKSITE_CITY="Palo Alto", WORKSITE_STATE="CA"))[1] == "San Francisco Bay Area"
    assert bsp.keep(row(SOC_CODE="15-1252.00", JOB_TITLE="Software Engineer")) is None


def test_occupation_mapping_is_the_stated_one():
    assert bsp.occupation("13-2051.00", "Analyst") == "corporate_finance_strategy"
    assert bsp.occupation("11-3031.01", "Treasurer") == "corporate_finance_strategy"
    assert bsp.occupation("13-1199.00", "Corporate Strategy Manager") == "corporate_finance_strategy"
    assert bsp.occupation("13-1199.00", "Buyer") is None
    assert bsp.occupation("11-2021.00", "Senior Product Manager") == "product_management"
    assert bsp.occupation("11-2021.00", "Product Marketing Manager") is None
    assert bsp.occupation("51-1011.00", "Product Manager") is None                  # outside major groups 11/13/15


def test_wage_annualization_and_aggregation():
    assert bsp.annual_wage(50, "Hour") == 104000 and bsp.annual_wage("10,000", "Month") == 120000 and bsp.annual_wage(None, "Year") is None
    out = bsp.aggregate([row(), row(WAGE_RATE_OF_PAY_FROM=210000), row(CASE_STATUS="Denied"), row(WORKSITE_CITY="Seattle", WORKSITE_STATE="WA")])
    boston = next(r for r in out if r["metro"] == "Boston")
    assert boston["filings"] == 2 and boston["median_annual_wage"] == 200000
    assert {r["metro"] for r in out} == {"Boston", "Seattle"}


def test_filtered_dataset_and_provenance_are_present_and_consistent():
    prov = json.loads((DATA / "provenance.json").read_text(encoding="utf-8"))
    assert prov["source_page"].startswith("https://www.dol.gov/") and prov["fiscal_year"] == 2025 and prov["files"]
    assert all(f["sha256"] and f["source_url"].startswith("https://www.dol.gov/") for f in prov["files"])
    with (DATA / "lca_filtered.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows and sum(int(r["filings"]) for r in rows) == prov["output"]["total_filings"]
    assert {r["metro"] for r in rows} <= set(sp.METROS) and {r["occupation"] for r in rows} <= set(sp.OCCUPATIONS)
    assert (DATA / "lca_filtered.csv").stat().st_size < 500_000                      # small enough to commit and test with


# ---------- alias matching ----------
def test_alias_matching_is_exact_not_fuzzy():
    school, lca = sp.aliases()
    assert school and lca
    assert sp.norm("  McKinsey &  Company ") == "mckinsey & company"
    for k in lca:                                   # every alias key is a full normalized name, not a fragment
        assert k == sp.norm(k) and len(k) > 3
    assert lca.get(sp.norm("McKinsey")) is None or sp.norm("McKinsey") in lca   # only explicitly reviewed strings match


def test_alias_table_is_reviewed():
    with (DATA / "employer_aliases.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows and all(r["alias_source"] in ("school_evidence", "lca") and r["reviewed_note"].strip() for r in rows)


# ---------- join + tool ----------
def test_join_uses_only_verified_school_lists():
    ev = sp.get_sponsorship_evidence("chicago-booth-mba")
    assert ev["status"] == "ok" and ev["note"] == sp.SPONSORSHIP_NOTE
    assert ev["school_list"]["evidence_id"].startswith("sx-chicago-booth-mba-hiring-employers")
    listed = {e["as_listed_by_school"] for e in ev["employers"]} | set(ev["unmatched_school_employers"])
    from backend.app.tools.supplementary import by_id
    assert listed == set(by_id(ev["school_list"]["evidence_id"]).value)
    for e in ev["employers"]:
        assert e["total_filings"] == sum(f["filings"] for f in e["filings"])
        for f in e["filings"]:
            assert sp.resolve(f["evidence_id"])["filings"] == f["filings"]


def test_programs_without_employer_evidence_stay_unknown():
    for pid in ("hbs-mba", "rice-jones-mba", "wharton-mba"):
        ev = sp.get_sponsorship_evidence(pid)
        assert ev["status"] == "no_employer_evidence" and ev["employers"] == []


def test_mit_list_from_red_marked_employers_joins():
    """MIT's list comes from the colour-coded official report (scripts/extract_mit_employers.py) and joins to DOL data."""
    ev = sp.get_sponsorship_evidence("mit-sloan-mba")
    assert ev["status"] == "ok" and "mitsloan.mit.edu" in ev["school_list"]["source_url"]
    assert {"JPMorgan Chase", "NVIDIA", "Fidelity Investments"} <= {e["employer"] for e in ev["employers"] if e["total_filings"]}
    assert {"Johnson & Johnson", "NextEra Energy"} <= set(ev["unmatched_school_employers"])   # reviewed: different firms only


def test_filters_narrow_results():
    full = sp.get_sponsorship_evidence("chicago-booth-mba")
    scoped = sp.get_sponsorship_evidence("chicago-booth-mba", "management_consulting", "Boston")
    for e in scoped["employers"]:
        assert all(f["occupation"] == "management_consulting" and f["metro"] == "Boston" for f in e["filings"])
    assert sum(e["total_filings"] for e in scoped["employers"]) <= sum(e["total_filings"] for e in full["employers"])
    assert sp.metro_for("Boston, MA") == "Boston" and sp.occupation_for("Management consulting") == "management_consulting"


def test_agent_tool_returns_evidence_ids_and_note():
    tb = ToolBox(default_store(), budget=type("B", (), {"check_tool": lambda self: None})(), log=lambda *a: None)
    out = json.loads(tb.call("evidence_analyst", "get_sponsorship_evidence", json.dumps({"program_id": "duke-fuqua-mba"})))
    data = out["data"]
    assert data["note"] == sp.SPONSORSHIP_NOTE and "untrusted" in out["note"].lower()
    assert all(f["evidence_id"].startswith("lca-fy2025-") for e in data["employers"] for f in e["filings"])
    assert "get_sponsorship_evidence" in ToolBox.SPECS


# ---------- guarantee blocking ----------
@pytest.mark.parametrize("text", ["McKinsey will sponsor your H-1B.", "Bain is likely to sponsor international MBAs.",
                                  "Amazon always sponsors visas.", "You will get an H-1B at Google.", "This employer sponsors visas for all hires.",
                                  "Graduates can obtain sponsorship at Goldman Sachs."])
def test_guarantee_language_is_blocked(text):
    assert "sponsorship_guarantee" in risky_language(text)


@pytest.mark.parametrize("text", [sp.SPONSORSHIP_NOTE, "McKinsey filed 40 H-1B labor condition applications in FY2025.",
                                  "Past filings do not mean the employer will sponsor you."])
def test_historical_statements_are_allowed(text):
    assert risky_language(text) == []


def test_grounding_accepts_lca_ids_and_checks_numbers():
    store = default_store()
    ev = sp.get_sponsorship_evidence("chicago-booth-mba")
    row_ = next(f for e in ev["employers"] for f in e["filings"])
    ok = Claim(text=f"{row_['filings']} certified H-1B filings in FY{row_['fiscal_year']} (historical).", label="verified_fact", evidence_ids=[row_["evidence_id"]])
    assert check_claim(store, ok) == []
    bad = Claim(text="98765 certified H-1B filings.", label="verified_fact", evidence_ids=[row_["evidence_id"]])
    assert any("not found in cited evidence" in p for p in check_claim(store, bad))
    fake = Claim(text="Filed H-1B.", label="verified_fact", evidence_ids=["lca-fy2025-made-up-000000"])
    assert any("does not exist" in p for p in check_claim(store, fake))


def test_ui_endpoints_carry_the_exact_note():
    c = TestClient(app)
    d = c.get("/api/programs/chicago-booth-mba").json()
    assert d["h1b_history"]["note"] == sp.SPONSORSHIP_NOTE
    dash = c.get("/api/dashboard/demo").json()["dashboard"]
    assert all(p["feasibility"]["h1b_history"]["note"] == sp.SPONSORSHIP_NOTE for p in dash["programs"])


def test_negated_guarantee_framing_is_not_flagged():
    """Found in a live run: 'Do not treat historical employer filings as a guarantee' was wrongly flagged."""
    assert risky_language("Do not treat historical employer filings as a guarantee of sponsorship.") == []
    assert risky_language("Past filings do not imply a guarantee.") == []
    assert "guarantee" in risky_language("It is not cheap, but it guarantees a job.")   # negation in another clause doesn't count
    assert "guarantee" in risky_language("This MBA guarantees you an H-1B.")
