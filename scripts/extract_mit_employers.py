"""Extract MIT Sloan's top hiring employers from its OFFICIAL 2025-2026 MBA Employment Report (PDF).

The report lists every employer and marks top hirers only by colour; its own legend says:
  "Red= Employers hiring three or more MIT Sloan MBA students for full-time and/or summer positions."
Plain-text extraction loses colour, so this script reads character colours with pdfplumber (dev-only dependency),
keeps the red words, joins adjacent words on the same line (one line = one employer), and writes the raw record
for scripts/build_supplementary.py (which then re-validates every name against the live PDF text).

    .venv\\Scripts\\python scripts\\extract_mit_employers.py
"""
import io
import json
from pathlib import Path

import httpx
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
URL = "https://mitsloan.mit.edu/sites/default/files/2026-03/2025-2026-MBA-Employment-Report.pdf"
OUT = ROOT / "data" / "sources" / "raw" / "supp" / "official_top_employers_mit.json"
RED = {(0.612, 0.114, 0.196), (0.639, 0.122, 0.204)}
LEGEND_WORDS = {"Red", "Red="}


def red_lines(page) -> list[dict]:
    words = [w for w in page.extract_words(extra_attrs=["non_stroking_color"])
             if tuple(round(x, 3) for x in (w["non_stroking_color"] or ())) in RED and w["text"] not in LEGEND_WORDS]
    words.sort(key=lambda w: (round(w["top"]), w["x0"]))
    lines: list[dict] = []
    for w in words:   # same line and adjacent -> same line segment
        ln = next((l for l in lines if abs(l["top"] - w["top"]) < 1.5 and 0 <= w["x0"] - l["x1"] < 12), None)
        if ln:
            ln["text"] += " " + w["text"]; ln["x1"] = w["x1"]
        else:
            lines.append({"text": w["text"], "x0": w["x0"], "x1": w["x1"], "top": w["top"], "bottom": w["bottom"]})
    # Each employer occupies exactly one line in this report (checked: no name wraps), so one red line = one name.
    return sorted(lines, key=lambda l: (round(l["x0"] / 40), l["top"]))


def main() -> None:
    r = httpx.get(URL, headers={"User-Agent": "AdmitCompass-research/1.0 (MGT 409 course project)"}, timeout=60, follow_redirects=True)
    r.raise_for_status()
    pdf = pdfplumber.open(io.BytesIO(r.content))
    text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    assert "Red= Employers hiring three or more MIT Sloan MBA students" in text, "legend not found; the report layout changed"
    names = []
    for page in pdf.pages:
        if "Employers Hiring" in (page.extract_text() or ""):
            names += [n["text"] for n in red_lines(page)]
    names = sorted(dict.fromkeys(n.rstrip("*").strip() for n in names), key=str.lower)
    rec = [{"program_id": "mit-sloan-mba", "field": "hiring_employers", "value": names, "unit": "text", "period": "Classes of 2025 and 2026",
            "period_basis": "cohort", "source_url": URL, "publisher": "MIT Sloan School of Management", "source_type": "official",
            "value_kind": "published", "excerpt": "Red= Employers hiring three or more MIT Sloan MBA students for full-time and/or summer positions.",
            "retrieved_on": "2026-10-24", "status": "found",
            "notes": ("Employers marked red in the official report = hired 3+ MIT Sloan MBA students for full-time and/or summer "
                      "(internship) positions, Classes of 2025-2026. Includes internships, so it is not a full-time-only list. "
                      "Extracted by text colour (scripts/extract_mit_employers.py).")}]
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
    print(len(names), "names:", names)


if __name__ == "__main__":
    main()
