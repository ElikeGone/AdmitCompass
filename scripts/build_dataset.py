"""Build data/programs/programs.json, data/sources/source_registry.json, and experiments/source_audit.json.

Inputs (all gathered 2026-10-23 from official university pages):
  * tier 1 - data/sources/raw/<program_id>.json : the original six, curated in Step 4 (highest priority)
  * tier 2 - data/sources/raw/enrich/batch*.json : enrichment of discovered programs (Step 9B)
Merge rule: tier 1 always wins. Tier 2 may only FILL fields tier 1 left unknown, never overwrite a verified fact.

Deterministic: no model calls. Facts are only marked verified if the raw file had a value from a fetched
official page AND the field is not in DOWNGRADE (values the collector flagged as unreliable).
Usage: .venv\\Scripts\\python scripts\\build_dataset.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.schemas.programs import FACT_NAMES, ProgramDataset  # noqa: E402

RAW = ROOT / "data" / "sources" / "raw"
CHECKED_ON = "2026-10-23"

PROGRAMS = {
    "yale-som-mba": ("Yale University", "Yale School of Management", "Full-Time MBA", "Yale School of Management"),
    "hbs-mba": ("Harvard University", "Harvard Business School", "MBA Program", "Harvard Business School"),
    "mit-sloan-mba": ("Massachusetts Institute of Technology", "MIT Sloan School of Management", "MBA Program", "MIT Sloan School of Management"),
    "chicago-booth-mba": ("University of Chicago", "Booth School of Business", "Full-Time MBA", "University of Chicago Booth School of Business"),
    "duke-fuqua-mba": ("Duke University", "Fuqua School of Business", "Daytime MBA", "Duke University Fuqua School of Business"),
    "rice-jones-mba": ("Rice University", "Jones Graduate School of Business", "Full-Time MBA", "Rice University Jones Graduate School of Business"),
}
# Normalized city/state from the raw location text (raw excerpt retained as evidence).
LOCATIONS = {
    "yale-som-mba": ("New Haven", "CT"), "mit-sloan-mba": ("Cambridge", "MA"),
    "chicago-booth-mba": ("Chicago", "IL"), "duke-fuqua-mba": ("Durham", "NC"), "rice-jones-mba": ("Houston", "TX"),
}
# Fields the collector flagged as unreliable -> recorded as UNKNOWN, candidate value kept only in the note.
DOWNGRADE = {
    ("duke-fuqua-mba", "industry_breakdown"): "PDF text extraction misaligned labels and percentages; values were re-matched by hand.",
    ("duke-fuqua-mba", "function_breakdown"): "PDF text extraction misaligned labels and percentages; values were re-matched by hand.",
    ("rice-jones-mba", "industry_breakdown"): "PDF text extraction scrambled the table; row-to-percent mapping uncertain.",
    ("rice-jones-mba", "international_employment"): "PDF text extraction scrambled the table; column mapping uncertain.",
    ("mit-sloan-mba", "function_breakdown"): "Report narrative and report table disagree (38.5% vs 38.9% for Consulting/Strategic Planning).",
    # --- Step 9B enrichment review (main session) ---
    ("kellogg-mba", "cost_of_attendance"): "Page labels the figure 'estimated first-year expenses'; not clearly the cost-of-attendance budget.",
    ("berkeley-haas-mba", "cost_of_attendance"): "California-resident budget; does not apply to international (non-resident) applicants.",
    ("wharton-mba", "median_base_salary"): "Page does not state that the median is base salary.",
    ("nyu-stern-mba", "median_base_salary"): "Page labels it 'median salary' without saying base salary.",
    ("ucla-anderson-mba", "tuition"): "Page gives 'program fees' including a summer term, not one-year tuition.",
    ("ut-mccombs-mba", "tuition"): "Recorded value is the Texas-resident rate; international applicants pay the non-resident rate.",
    ("ut-mccombs-mba", "cost_of_attendance"): "Recorded value is the Texas-resident budget; international applicants pay the non-resident rate.",
    ("unc-kenan-flagler-mba", "tuition"): "Recorded value is the North Carolina-resident rate; international applicants pay the non-resident rate.",
    ("unc-kenan-flagler-mba", "cost_of_attendance"): "Recorded value is the North Carolina-resident budget; international applicants pay the non-resident rate.",
    ("unc-kenan-flagler-mba", "international_employment"): "Read from PDF layout; the label-to-number association is uncertain.",
    ("texas-am-mays-mba", "tuition"): "Page gives no academic year and doesn't say whether the figure is annual or for the whole program.",
    ("texas-am-mays-mba", "stem_designation"): "Page only says the MS Analytics dual degree is STEM-designated; silence is not evidence that the MBA is not designated.",
    ("minnesota-carlson-mba", "stem_designation"): "Page makes no STEM statement for the standard Full-Time MBA; silence is not evidence either way.",
    ("minnesota-carlson-mba", "employment_rate"): "Combines Classes of 2023-2025 and two different MBA programs; not a single-cohort program figure.",
    ("minnesota-carlson-mba", "industry_breakdown"): "Combines Classes of 2023-2025 and two different MBA programs.",
    ("minnesota-carlson-mba", "function_breakdown"): "Combines Classes of 2023-2025 and two different MBA programs.",
    ("cornell-johnson-mba", "stem_designation"): "Spot check (2026-10-23): the page calls the curriculum 'STEM designated' but makes no statement that the MBA degree is STEM-designated.",
}
UNITS = {
    "location": "location", "duration_months": "months", "application_requirements": "text_list",
    "test_policy": "text", "tuition": "USD", "cost_of_attendance": "USD", "stem_designation": "stem",
    "employment_rate": "percent", "median_base_salary": "USD", "industry_breakdown": "percent_map",
    "function_breakdown": "percent_map", "international_employment": "text", "sponsorship": "sponsorship",
    "application_deadlines": "text_list",
}
ENRICH = RAW / "enrich"
MIN_PROMOTE = 2
NOT_FETCHED = re.compile(r"not\s+fetched|wasn'?t\s+fetched|did\s+not\s+fetch|not\s+(visited|reached|opened)|could\s*n[o']?t\s+(fetch|parse|decode)|exceeded", re.I)
# Facts independently re-fetched by the main session (second check), 2026-10-23.
SPOT_CHECKS = [
    {"program_id": "yale-som-mba", "fields": ["tuition", "cost_of_attendance"], "url": "https://som.yale.edu/programs/mba/affording-your-mba/cost-information", "result": "match ($90,900; $128,976; 2026-27)"},
    {"program_id": "chicago-booth-mba", "fields": ["tuition", "cost_of_attendance"], "url": "https://www.chicagobooth.edu/mba/full-time/admissions/cost", "result": "match ($89,976; $132,449; 2026-27)"},
    {"program_id": "mit-sloan-mba", "fields": ["stem_designation"], "url": "https://mitsloan.mit.edu/mba/explore-program", "result": "match ('The MIT Sloan MBA is a STEM-designated program.')"},
    # Step 9B spot checks of enrichment facts
    {"program_id": "stanford-gsb-mba", "fields": ["tuition", "cost_of_attendance"], "url": "https://www.gsb.stanford.edu/programs/mba/tuition-financial-aid/cost-attendance", "result": "match ($89,187; $140,940; First-Year MBA 2026-2027)"},
    {"program_id": "dartmouth-tuck-mba", "fields": ["median_base_salary", "employment_rate"], "url": "https://tuck.dartmouth.edu/mba/career-services/employment-statistics", "result": "match ('The median base salary for the class of 2025 is $175,000'; '90% ... received an offer and 87% accepted')"},
    {"program_id": "cmu-tepper-mba", "fields": ["tuition", "cost_of_attendance"], "url": "https://www.cmu.edu/sfs/tuition/graduate/tepper/full-accel-mba.html", "result": "match ($84,186; $120,798; 2026-2027 standard single budget)"},
    {"program_id": "cornell-johnson-mba", "fields": ["stem_designation"], "url": "https://business.cornell.edu/admissions/graduate/full-time-mba/", "result": "mismatch: curriculum described as STEM designated; no degree designation stated -> downgraded"},
]
SPONSORSHIP_NOTE = ("No employer-specific visa sponsorship evidence on official program pages. Employer lists in "
                    "employment reports are NOT evidence of sponsorship.")
STEM_NOTE = ("STEM designation is a program classification; it does not by itself guarantee any immigration benefit "
             "(e.g., STEM OPT also depends on the student's status, employer E-Verify enrollment, and USCIS approval).")


def norm_period(name: str, raw: str | None) -> str | None:
    if not raw:
        return None
    if name in ("tuition", "cost_of_attendance"):
        m = re.search(r"(\d{4})\s*[-–]\s*(\d{2,4})", raw)
        if m:
            start, end = int(m.group(1)), m.group(2)
            end = int(end) if len(end) == 4 else int(str(start)[:2] + end)
            return f"{start}-{end}"
        return raw
    m = re.search(r"Class of (\d{4})(?:-(\d{2}))?", raw)
    if m:
        return f"Class of {int(str(m.group(1))[:2] + m.group(2)) if m.group(2) else m.group(1)}"
    return raw


def merge_raw(primary: dict | None, secondary: dict | None) -> dict:
    """Fill-only merge: keep every verified field of `primary`; take a field from `secondary` only where primary is null."""
    if not primary:
        return secondary or {}
    if not secondary:
        return primary
    out = json.loads(json.dumps(primary))
    for name, val in (secondary.get("facts") or {}).items():
        if val and not (out.get("facts") or {}).get(name):
            out.setdefault("facts", {})[name] = val
            out.setdefault("_filled_from_secondary", []).append(name)
            out.setdefault("urls_checked", []).extend(u for u in secondary.get("urls_checked", []) if u.get("url") == val.get("source_url"))
    return out


def discovery_locations() -> dict[str, dict]:
    """university -> {city, state, url, excerpt} for discovery records whose location was quoted from a fetched page."""
    f = ROOT / "data" / "discovery" / "discovered_programs.json"
    if not f.exists():
        return {}
    out = {}
    for d in json.loads(f.read_text(encoding="utf-8"))["programs"]:
        basis = d.get("location_basis") or ""
        if d.get("fetched") and d.get("city") and d.get("state") and basis.startswith("stated on fetched page"):
            m = re.search(r'["\u201c](.+?)["\u201d]', basis)
            if m:
                out[d["university"]] = {"city": d["city"], "state": d["state"], "url": d["provenance_url"],
                                        "title": d.get("page_title") or d["provenance_url"], "excerpt": m.group(1)}
    return out


def load_raw() -> dict[str, dict]:
    """program_id -> raw record with metadata, facts, unknown_reasons, urls_checked, tier."""
    recs: dict[str, dict] = {}
    disc_loc = discovery_locations()
    for pid, (uni, school, pname, publisher) in PROGRAMS.items():
        r = json.loads((RAW / f"{pid}.json").read_text(encoding="utf-8"))
        recs[pid] = {**r, "university": uni, "school": school, "program_name": pname, "publisher": publisher, "tier": "curated",
                     "unknown_reasons": {n: "checked" for n in FACT_NAMES if n != "application_deadlines"}}
    for f in (sorted(ENRICH.glob("batch*.json")) if ENRICH.exists() else []):
        for r in json.loads(f.read_text(encoding="utf-8"))["programs"]:
            r = {**r, "publisher": r.get("school") or r["university"], "tier": "enriched", "batch": f.name}
            loc = disc_loc.get(r["university"])
            if loc and not (r.get("facts") or {}).get("location"):
                r.setdefault("facts", {})["location"] = {"value": {"city": loc["city"], "state": loc["state"]}, "unit": "location",
                    "period": None, "definition": "From the discovery pass: location quoted on the fetched official program page",
                    "source_url": loc["url"], "source_title": loc["title"], "excerpt": loc["excerpt"], "excerpt_is_paraphrase": False}
                r.setdefault("urls_checked", []).append({"url": loc["url"], "title": loc["title"], "accessible": True, "note": "discovery pass"})
            recs[r["program_id"]] = merge_raw(recs[r["program_id"]], r) if r["program_id"] in recs else r
    return recs


def main() -> int:
    programs, sources, audit_programs, not_promoted = [], {}, [], []
    url_to_id: dict[str, str] = {}
    raws = load_raw()

    def source_id_for(pid: str, url: str, title: str, accessible: bool, note: str = "") -> str:
        if url in url_to_id:
            s = sources[url_to_id[url]]
            if accessible and not s["accessed"]:
                s.update(accessed=True, checked_on=CHECKED_ON)
            return url_to_id[url]
        sid = f"src-{pid}-{sum(1 for k in url_to_id.values() if k.startswith(f'src-{pid}-')) + 1:02d}"
        url_to_id[url] = sid
        sources[sid] = {"source_id": sid, "url": url, "title": (title or url)[:200], "publisher": raws[pid]["publisher"],
                        "source_type": "official_university", "accessed": accessible,
                        "checked_on": CHECKED_ON if accessible else None, "note": (note or "")[:300]}
        return sid

    for pid, raw in raws.items():
        for u in raw.get("urls_checked", []):
            note = u.get("note", "") or ""
            if "uconnectlabs" in u["url"]:
                note = (note + " Hosted on the career office's vendor CDN; linked from the official reports page.").strip()
            source_id_for(pid, u["url"], u.get("title", ""), bool(u.get("accessible")), note)

        facts, evidence = {}, []
        verified, unknown, downgraded, not_checked = [], [], [], []
        reasons = raw.get("unknown_reasons") or {}
        for name in FACT_NAMES:
            r = (raw.get("facts") or {}).get(name)
            unit = UNITS[name]
            loc_ok = name != "location" or pid in LOCATIONS or bool(
                r and isinstance(r.get("value"), dict) and r["value"].get("city") and r["value"].get("state"))
            if r is None or (pid, name) in DOWNGRADE or not loc_ok:
                why = str(reasons.get(name, "not_checked" if name == "application_deadlines" else "checked"))
                # "checked" only if the collector actually looked at the relevant page; a reason that says the page
                # was not fetched means the fact was NOT checked, whatever label the collector used.
                checked = not why.lower().startswith("not") and not NOT_FETCHED.search(why)
                note = ""
                if (pid, name) in DOWNGRADE:
                    note = f"Not verified: {DOWNGRADE[(pid, name)]} Candidate value (unverified): {json.dumps(r['value'])[:300]}"
                    downgraded.append(name)
                elif name == "sponsorship":
                    note = SPONSORSHIP_NOTE
                elif name == "application_deadlines" and raw["tier"] == "curated" and not checked:
                    note = "Not collected in the original evidence pass."
                elif ":" in why:
                    note = why.split(":", 1)[1].strip()[:280]
                facts[name] = {"status": "unknown", "unit": unit, "note": note, "checked": checked}
                (unknown if checked else not_checked).append(name)
                continue
            sid = source_id_for(pid, r["source_url"], r.get("source_title", ""), True)
            eid = f"ev-{pid}-{name.replace('_', '-')}"
            evidence.append({"evidence_id": eid, "source_id": sid, "excerpt": r["excerpt"][:600],
                             "excerpt_is_paraphrase": bool(r.get("excerpt_is_paraphrase")),
                             "rechecked": any(c["program_id"] == pid and name in c["fields"] and c["result"].startswith("match")
                                              for c in SPOT_CHECKS)})
            value = r["value"]
            if name == "location":
                value = ({"city": LOCATIONS[pid][0], "state": LOCATIONS[pid][1]} if pid in LOCATIONS
                         else {"city": value["city"], "state": value["state"]})
            outcome = name in ("employment_rate", "median_base_salary", "industry_breakdown", "function_breakdown")
            note = "" if outcome else (r.get("definition") or "")
            if name == "stem_designation":
                note = (f"{r.get('definition') or ''} {STEM_NOTE}").strip()
                if r.get("period"):
                    note = f"Applies: {r['period']}. " + note
            definition = r.get("definition") if outcome else None
            period = None if name in ("stem_designation", "application_requirements") else norm_period(name, r.get("period"))
            if name in ("tuition", "cost_of_attendance") and r.get("period"):
                note = f"Source period: {r['period']}. {note}".strip()
            facts[name] = {"status": "verified", "value": value, "unit": unit, "period": period,
                           "definition": definition, "evidence_ids": [eid], "note": note[:500]}
            verified.append(name)

        # Safe promotion: an enriched program joins the evidence store only with >= MIN_PROMOTE verified facts
        # beyond its location. Otherwise it stays in the discovery tier (its record there is untouched).
        if raw["tier"] == "enriched" and len([v for v in verified if v != "location"]) < MIN_PROMOTE:
            not_promoted.append({"program_id": pid, "verified_fields": verified, "reason": f"fewer than {MIN_PROMOTE} verified facts beyond location"})
            continue
        programs.append({"program_id": pid, "university": raw["university"], "school": raw["school"],
                         "program_name": raw["program_name"], "degree": "MBA", "collection_tier": raw["tier"],
                         "facts": facts, "evidence": evidence})
        audit_programs.append({
            "program_id": pid, "tier": raw["tier"], "batch": raw.get("batch"),
            "urls_checked": [{"url": u["url"], "accessible": bool(u.get("accessible")), "note": u.get("note", "")}
                             for u in raw.get("urls_checked", [])],
            "inaccessible_urls": [u["url"] for u in raw.get("urls_checked", []) if not u.get("accessible")],
            "verified_fields": verified, "unknown_checked_fields": unknown, "not_checked_fields": not_checked,
            "downgraded_to_unknown": {n: DOWNGRADE[(pid, n)] for n in downgraded},
            "paraphrased_excerpts": [n for n in verified if raw["facts"][n].get("excerpt_is_paraphrase")],
        })

    dataset = {"schema_version": "1.1", "collected_on": CHECKED_ON, "programs": programs}
    registry = {"schema_version": "1.0", "sources": list(sources.values())}
    ProgramDataset(schema_version="1.1", programs=programs, sources=registry["sources"])  # validate before writing

    (ROOT / "data" / "programs" / "programs.json").write_text(json.dumps(dataset, indent=2), encoding="utf-8")
    (ROOT / "data" / "sources" / "source_registry.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")

    total = len(programs) * len(FACT_NAMES)
    n_ver = sum(len(p["verified_fields"]) for p in audit_programs)
    per_field = Counter(f for p in audit_programs for f in p["verified_fields"])
    audit = {
        "generated_by": "scripts/build_dataset.py", "collection_date": CHECKED_ON,
        "method": ("Research subagents (Claude Code) fetched official university pages with WebFetch/WebSearch and recorded URL, "
                   "title and excerpt per field (6 curated programs in Step 4; enrichment batches in Step 9B). Some excerpts are "
                   "fetch-tool paraphrases (flagged). No LLM inference was used to fill missing values. Spot checks list the facts "
                   "independently re-fetched by the main session."),
        "spot_checks": SPOT_CHECKS,
        "programs": audit_programs,
        "not_promoted": not_promoted,
        "coverage": {
            "programs": len(programs), "fields_per_program": len(FACT_NAMES), "total_fields": total,
            "verified_fields": n_ver, "unknown_fields": total - n_ver,
            "verified_pct": round(100 * n_ver / total, 1),
            "not_checked_fields": sum(len(p["not_checked_fields"]) for p in audit_programs),
            "verified_by_field": {f: f"{per_field.get(f, 0)}/{len(programs)}" for f in FACT_NAMES},
            "sources_total": len(sources), "sources_accessed": sum(s["accessed"] for s in sources.values()),
            "sources_inaccessible": sum(not s["accessed"] for s in sources.values()),
            "source_types": dict(Counter(s["source_type"] for s in sources.values())),
            "paraphrased_excerpts": sum(len(p["paraphrased_excerpts"]) for p in audit_programs),
            "downgraded_to_unknown": sum(len(p["downgraded_to_unknown"]) for p in audit_programs),
            "by_tier": dict(Counter(p["tier"] for p in audit_programs)),
        },
    }
    (ROOT / "experiments" / "source_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit["coverage"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
