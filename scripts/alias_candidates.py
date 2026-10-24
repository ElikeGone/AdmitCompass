"""List CANDIDATE LCA employer names for each school-listed employer, to support a MANUAL alias review.

Nothing here is used at runtime and nothing is matched automatically: a person reads this list and writes the accepted
pairs into data/sponsorship/employer_aliases.csv. Candidates = LCA names containing a distinctive word of the school name.

    .venv\\Scripts\\python scripts\\alias_candidates.py > experiments/sponsorship/alias_candidates.txt
"""
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STOP = {"inc", "llc", "llp", "lp", "ltd", "corp", "corporation", "company", "co", "the", "group", "and", "of", "us", "u.s.", "plc",
        "financial", "partners", "consulting", "capital", "management", "bank", "services", "holdings", "global", "america",
        "international", "technologies", "technology", "strategy", "logo", "american", "trust", "general"}
lca = Counter()
with (ROOT / "data" / "sponsorship" / "lca_filtered.csv").open(encoding="utf-8") as f:
    for r in csv.DictReader(f):
        lca[r["employer_name"]] += int(r["filings"])
supp = json.loads((ROOT / "data" / "programs" / "supplementary.json").read_text(encoding="utf-8"))["facts"]
names = sorted({n for x in supp if x["field"] == "hiring_employers" and x["status"] == "verified" for n in x["value"]})
for n in names:
    words = [w for w in re.findall(r"[a-z0-9&]+", n.lower().replace("&", " & ")) if w not in STOP and len(w) >= 3]
    cands = sorted(((c, k) for c, k in lca.items() if any(re.search(rf"\b{re.escape(w)}\b", c.lower()) for w in words)), key=lambda t: -t[1])
    print(f"## {n}   (key words: {words})")
    for c, k in cands[:12]:
        print(f"    {k:5d}  {c}")
