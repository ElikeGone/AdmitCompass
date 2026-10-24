"""Build data/discovery/discovered_programs.json from raw collection notes in data/discovery/raw/.

Deterministic, no model calls. Each record only states that a program exists, where we learned it
(official university page), and where it is. No cost, outcome, STEM, or sponsorship fields exist.
Usage: .venv\\Scripts\\python scripts\\build_discovery_index.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.schemas.discovery import DiscoveryIndex  # noqa: E402
from backend.app.tools.catalog import Catalog  # noqa: E402
from backend.app.tools.evidence_store import EvidenceStore  # noqa: E402

RAW = ROOT / "data" / "discovery" / "raw"
OUT = ROOT / "data" / "discovery" / "discovered_programs.json"
BUILT_ON = "2026-10-23"
# Collector notes that explain a weaker location basis (kept transparent in the record).
LOCATION_OVERRIDES = {
    "University of North Carolina at Chapel Hill":
        "inferred: official FAQ page names 'Chapel Hill' and 'North Carolina' separately; not a literal address",
}


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main() -> int:
    programs = []
    for f in sorted(RAW.glob("batch*.json")):
        for p in json.loads(f.read_text(encoding="utf-8"))["programs"]:
            fetched = bool(p.get("fetched"))
            basis = LOCATION_OVERRIDES.get(p["university"]) or (p.get("location_basis") or "not recorded")
            name = re.sub(r"\s*\(page also says.*\)$", "", p["program_name"]).strip()
            notes = (p.get("notes") or "").strip()
            if p.get("excerpt_url"):
                notes = (notes + f" Excerpt taken from {p['excerpt_url']}.").strip()
            if p.get("location_url") and basis.startswith("not on fetched page") and p.get("city"):
                basis = f"{basis}; location from {p['location_url']}"
            programs.append({
                "discovery_id": f"disc-{slug(p['university'])}-mba",
                "university": p["university"], "school": p.get("school"), "program_name": name,
                "degree_type": "MBA", "format": p.get("format") or "full-time",
                "city": p.get("city") if fetched else None, "state": p.get("state") if fetched else None,
                "location_basis": basis[:300], "provenance_url": p["official_url"],
                "page_title": p.get("page_title"), "excerpt": (p.get("excerpt") or None) and p["excerpt"][:400],
                "discovered_on": BUILT_ON, "fetched": fetched,
                "verification_status": "needs_verification" if fetched else "not_confirmed",
                "notes": notes[:500],
            })
    index = {
        "schema_version": "1.0", "built_on": BUILT_ON, "is_live_search": False,
        "method": ("Periodically built index (not a live search). Three research agents searched for each named program's "
                   "official page on the university's own domain and fetched it to confirm the program exists; only "
                   "existence, name, format, location and provenance were recorded."),
        "sources_note": ("Official university program pages (one per record, see provenance_url). The AACSB accredited-school "
                         "directory was evaluated as a seed list (see data/discovery/README.md) but not used for records."),
        "programs": programs,
    }
    DiscoveryIndex.model_validate(index)  # fail before writing
    OUT.write_text(json.dumps(index, indent=2), encoding="utf-8")
    cat = Catalog(EvidenceStore.load(), DiscoveryIndex.model_validate(index))
    print(json.dumps({"records": len(programs), "fetched": sum(p["fetched"] for p in programs), **cat.counts()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
