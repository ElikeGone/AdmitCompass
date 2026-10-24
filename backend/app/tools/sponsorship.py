"""Employer-specific H-1B evidence: verified program hiring-employer lists joined to DOL LCA filings.

Data:
  data/sponsorship/lca_filtered.csv      built by scripts/build_sponsorship.py from DOL OFLC disclosure files
  data/sponsorship/provenance.json       source URL, files, hashes, fiscal year, coverage, download date
  data/sponsorship/employer_aliases.csv  REVIEWED exact-match aliases (no fuzzy matching):
                                         canonical_employer, alias, alias_source (school_evidence | lca), reviewed_note
Matching is exact after trimming, collapsing whitespace and case-folding. A name with no alias row stays unmatched.
An LCA filing is historical evidence about an employer, never a promise that it will sponsor any person or role.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from functools import lru_cache

from ..core.config import REPO_ROOT

DIR = REPO_ROOT / "data" / "sponsorship"
SPONSORSHIP_NOTE = ("Historical H-1B filings by this employer. Not a guarantee of sponsorship. U.S. work-authorization rules change; "
                    "confirm with official sources and the school's international student office. Not legal advice.")
OCCUPATIONS = {"management_consulting": "Management consulting", "product_management": "Product management",
               "corporate_finance_strategy": "Corporate finance / strategy"}
METROS = ["Boston", "Seattle", "Houston", "New York", "San Francisco Bay Area"]
CITY_TO_METRO = {"boston": "Boston", "seattle": "Seattle", "houston": "Houston", "new york": "New York", "new york city": "New York",
                 "nyc": "New York", "manhattan": "New York", "san francisco": "San Francisco Bay Area", "bay area": "San Francisco Bay Area",
                 "san francisco bay area": "San Francisco Bay Area", "sf bay area": "San Francisco Bay Area", "silicon valley": "San Francisco Bay Area",
                 "san jose": "San Francisco Bay Area", "palo alto": "San Francisco Bay Area", "mountain view": "San Francisco Bay Area"}
TARGET_TO_OCCUPATION = [(re.compile(r"consult", re.I), "management_consulting"), (re.compile(r"product", re.I), "product_management"),
                        (re.compile(r"financ|strateg", re.I), "corporate_finance_strategy")]


def norm(name: str) -> str:
    return " ".join(str(name or "").split()).casefold()


def lca_id(canonical: str, occupation: str, metro: str, fy) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", canonical.lower()).strip("-")[:40]
    h = hashlib.sha1(f"{canonical}|{occupation}|{metro}|{fy}".encode()).hexdigest()[:6]
    return f"lca-fy{fy}-{slug}-{h}"


@lru_cache(maxsize=1)
def provenance() -> dict:
    p = DIR / "provenance.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


@lru_cache(maxsize=1)
def aliases() -> tuple[dict[str, str], dict[str, str]]:
    """(school-evidence name -> canonical, LCA employer name -> canonical)"""
    school, lca = {}, {}
    p = DIR / "employer_aliases.csv"
    if p.exists():
        with p.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                (school if r["alias_source"] == "school_evidence" else lca)[norm(r["alias"])] = r["canonical_employer"]
    return school, lca


@lru_cache(maxsize=1)
def lca_rows() -> tuple[dict, ...]:
    p = DIR / "lca_filtered.csv"
    if not p.exists():
        return ()
    from ..core.safety import injection_hits
    _, lca = aliases()
    out = []
    with p.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if injection_hits(r["employer_name"]):   # third-party text: instruction-like names are dropped, never shown to a model
                continue
            canon = lca.get(norm(r["employer_name"]))
            out.append({**r, "filings": int(r["filings"]), "worker_positions": int(r["worker_positions"]),
                        "median_annual_wage": int(r["median_annual_wage"]) if r["median_annual_wage"] else None, "canonical_employer": canon})
    return tuple(out)


def reload() -> None:
    for fn in (provenance, aliases, lca_rows):
        fn.cache_clear()


def _grouped() -> dict[tuple[str, str, str], dict]:
    """canonical employer + occupation + metro -> combined filings across that employer's LCA name variants."""
    g: dict[tuple, dict] = {}
    for r in lca_rows():
        if not r["canonical_employer"]:
            continue
        k = (r["canonical_employer"], r["occupation"], r["metro"])
        x = g.setdefault(k, {"filings": 0, "worker_positions": 0, "wages": [], "lca_names": set(), "fiscal_year": r["fiscal_year"],
                             "coverage": r.get("coverage", "")})
        x["filings"] += r["filings"]; x["worker_positions"] += r["worker_positions"]; x["lca_names"].add(r["employer_name"])
        if r["median_annual_wage"]:
            x["wages"].append((r["median_annual_wage"], r["filings"]))
    return g


def resolve(evidence_id: str) -> dict | None:
    """lca-... evidence id -> the aggregated row it stands for (used by grounding and citations)."""
    for (canon, occ, met), x in _grouped().items():
        if lca_id(canon, occ, met, x["fiscal_year"]) == evidence_id:
            return {"evidence_id": evidence_id, "employer": canon, "occupation": occ, "metro": met, "filings": x["filings"],
                    "worker_positions": x["worker_positions"], "fiscal_year": x["fiscal_year"], "coverage": x["coverage"],
                    "median_annual_wage": _wage(x), "lca_employer_names": sorted(x["lca_names"]),
                    "source_url": provenance().get("source_page"), "source_title": "U.S. DOL OFLC H-1B LCA disclosure data"}
    return None


def _wage(x: dict) -> int | None:
    # median of per-row medians, weighted by filings (rows are already medians; stated as an approximation)
    ws = sorted(w for w, n in x["wages"] for _ in range(n))
    return ws[len(ws) // 2] if ws else None


def occupation_for(text: str | None) -> str | None:
    for pat, occ in TARGET_TO_OCCUPATION:
        if text and pat.search(text):
            return occ
    return None


def metro_for(text: str | None) -> str | None:
    t = norm(text or "")
    return next((m for k, m in CITY_TO_METRO.items() if k == t or re.search(rf"\b{re.escape(k)}\b", t)), None)


def get_sponsorship_evidence(program_id: str, occupation: str | None = None, city: str | None = None) -> dict:
    """Per-employer historical H-1B LCA filings for employers that the program's OFFICIAL report says hired its graduates."""
    from . import supplementary as supp
    occ = occupation if occupation in OCCUPATIONS else occupation_for(occupation)
    met = city if city in METROS else metro_for(city)
    lst = next((f for f in supp.verified(program_id) if f.field == "hiring_employers"), None)
    base = {"program_id": program_id, "occupation": occ, "metro": met, "note": SPONSORSHIP_NOTE,
            "data_source": {k: provenance().get(k) for k in ("source", "source_page", "fiscal_year", "coverage", "quarters_used", "downloaded_on")}}
    if lst is None:
        gap = next((f for f in supp.load() if f.program_id == program_id and f.field == "hiring_employers"), None)
        return {**base, "status": "no_employer_evidence", "employers": [], "unmatched_school_employers": [],
                "reason": ("The program's official employment report doesn't list employers, or it couldn't be retrieved"
                           + (f" ({supp.GAP_REASON.get(gap.status, gap.status)})" if gap else "") + ".")}
    school, _ = aliases()
    grouped = _grouped()
    employers, unmatched = [], []
    for name in lst.value:
        canon = school.get(norm(name))
        if not canon:
            unmatched.append(name)
            continue
        rows = [(o, m, x) for (c, o, m), x in grouped.items() if c == canon and (occ is None or o == occ) and (met is None or m == met)]
        employers.append({
            "employer": canon, "as_listed_by_school": name, "school_evidence_id": lst.fact_id,
            "total_filings": sum(x["filings"] for _, _, x in rows),
            "filings": [{"evidence_id": lca_id(canon, o, m, x["fiscal_year"]), "occupation": o, "metro": m, "filings": x["filings"],
                         "median_annual_wage": _wage(x), "fiscal_year": x["fiscal_year"], "coverage": x["coverage"]}
                        for o, m, x in sorted(rows, key=lambda t: -t[2]["filings"])]})
    employers.sort(key=lambda e: -e["total_filings"])
    return {**base, "status": "ok", "school_list": {"evidence_id": lst.fact_id, "period": lst.period, "notes": lst.notes, "source_url": lst.source_url},
            "employers": employers, "unmatched_school_employers": unmatched,
            "matching_rule": "Exact match through the reviewed alias table; unmatched names are not guessed."}


QUESTION_SHORT_NAMES = {"McKinsey & Company": ["McKinsey"], "Boston Consulting Group": ["BCG"], "Bain & Company": ["Bain"],
                        "Goldman Sachs": ["Goldman"], "JPMorgan Chase": ["JPMorgan", "J.P. Morgan", "JP Morgan"],
                        "Deloitte Consulting": ["Deloitte"], "Morgan Stanley": ["Morgan Stanley"], "Kearney": ["A.T. Kearney"]}


def mentioned_employers(text: str) -> list[str]:
    """Canonical employers whose canonical name or a reviewed school alias appears in the text (word-boundary, case-insensitive)."""
    school, _ = aliases()
    names = {c: {c} for c in set(school.values())}
    for alias, canon in school.items():
        names[canon].add(alias)
    for canon, shorts in QUESTION_SHORT_NAMES.items():   # explicit short names people type in questions (not used for data joins)
        if canon in names:
            names[canon].update(shorts)
    t = norm(text)
    # "(?!\s+capital)": "Bain Capital" is a different firm from Bain & Company (same rule for any short name)
    return sorted(c for c, ns in names.items() if any(re.search(rf"(?<![a-z0-9]){re.escape(norm(n))}(?![a-z0-9])(?!\s+capital)", t) for n in ns))


def employer_filings(canonical: str, occupation: str | None = None, metro: str | None = None) -> list[dict]:
    """All historical filing groups for one canonical employer (not tied to any program), largest first."""
    rows = [(o, m, x) for (c, o, m), x in _grouped().items() if c == canonical and (occupation is None or o == occupation) and (metro is None or m == metro)]
    return [{"evidence_id": lca_id(canonical, o, m, x["fiscal_year"]), "occupation": o, "metro": m, "filings": x["filings"],
             "median_annual_wage": _wage(x), "fiscal_year": x["fiscal_year"]} for o, m, x in sorted(rows, key=lambda t: -t[2]["filings"])]
