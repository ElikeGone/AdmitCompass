"""Raw (UNVALIDATED) records: each program's rank in the Poets&Quants 2025-2026 U.S. MBA ranking.

Why this source: P&Q's ranking is itself a composite of five published rankings (U.S. News, Financial Times,
Bloomberg Businessweek, LinkedIn, Princeton Review), so one number summarises them without us scraping U.S. News.
Only the composite rank is stored (no reproduction of the table). scripts/build_supplementary.py re-fetches each
page and confirms "#N" appears in the same table row as the school before the rank becomes "verified".

Ranks are CONTEXT ONLY: never used in matching, default sorting, or any agent/copilot prompt.

    .venv\\Scripts\\python scripts\\make_ranking_raw.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "sources" / "raw" / "supp" / "secondary_pq_ranking_2025_2026.json"
BASE = "https://poetsandquants.com/2025/12/07/poets-and-quants-2025-2026-mba-ranking/"
EDITION = "Poets&Quants 2025-2026 ranking of the best U.S. MBA programs (published 2025-12-07)"
# program_id, row label (must appear in the table row), printed rank
RANKS = [
    ("kellogg-mba", "Northwestern (Kellogg)", "#1"), ("hbs-mba", "Harvard Business School", "#2"),
    ("disc-columbia-university-mba", "Columbia Business School", "#3"), ("dartmouth-tuck-mba", "Dartmouth (Tuck)", "#4"),
    ("uva-darden-mba", "Virginia (Darden)", "#5"), ("nyu-stern-mba", "New York (Stern)", "#6"), ("cornell-johnson-mba", "Cornell (Johnson)", "#7"),
    ("wharton-mba", "Pennsylvania (Wharton)", "#8"), ("michigan-ross-mba", "Michigan (Ross)", "#9"), ("ucla-anderson-mba", "UCLA (Anderson)", "#10"),
    ("mit-sloan-mba", "MIT (Sloan)", "#11"), ("chicago-booth-mba", "Chicago (Booth)", "#12"), ("ut-mccombs-mba", "Texas-Austin (McCombs)", "#13"),
    ("berkeley-haas-mba", "UC-Berkeley (Haas)", "#14"), ("duke-fuqua-mba", "Duke (Fuqua)", "#15"), ("cmu-tepper-mba", "Carnegie Mellon (Tepper)", "#16"),
    ("yale-som-mba", "Yale SOM", "#17"), ("vanderbilt-owen-mba", "Vanderbilt (Owen)", "#18"),
    ("georgia-tech-scheller-mba", "Georgia Institute of Technology (Scheller)", "#20"), ("unc-kenan-flagler-mba", "North Carolina (Kenan-Flagler)", "#21"),
    ("emory-goizueta-mba", "Emory (Goizueta)", "#22"), ("uw-foster-mba", "Washington (Foster)", "#23"), ("usc-marshall-mba", "Southern California (Marshall)", "#24"),
    ("georgetown-mcdonough-mba", "Georgetown (McDonough)", "#25"), ("stanford-gsb-mba", "Stanford GSB", "#26"), ("rice-jones-mba", "Rice (Jones)", "#27"),
    ("notre-dame-mendoza-mba", "Notre Dame (Mendoza)", "#28"), ("texas-am-mays-mba", "Texas A&M (Mays)", "#38"),
    ("disc-indiana-university-mba", "Indiana (Kelley)", "#39"), ("minnesota-carlson-mba", "Minnesota (Carlson)", "#43"),
]
recs = []
for pid, label, printed in RANKS:
    rank = int(printed.lstrip("#"))
    page = 3 + (rank - 1) // 25          # the article prints 25 schools per page, starting on page 3
    recs.append({"program_id": pid, "row_label": label, "printed": printed, "field": "ranking", "value": rank, "unit": "rank",
                 "period": "2025-2026 edition", "period_basis": "annual", "source_url": f"{BASE}{page}/", "publisher": "Poets&Quants",
                 "source_type": "secondary", "value_kind": "published", "retrieved_on": "2026-10-24",
                 "notes": f"{EDITION}. Composite of U.S. News, Financial Times, Bloomberg Businessweek, LinkedIn and Princeton Review. "
                          "Rankings reflect prestige; AdmitCompass ranks by career fit."})
OUT.write_text(json.dumps(recs, indent=1, ensure_ascii=False), encoding="utf-8")
print(len(recs), "ranking records ->", OUT)
