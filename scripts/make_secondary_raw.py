"""Write the raw (UNVALIDATED) secondary-source records for Poets&Quants and Clear Admit.

Values are transcribed exactly as printed (the `printed` string) so scripts/build_supplementary.py can independently
re-fetch each page and confirm the string appears in the same table row as the school. Nothing here is trusted
until that validation passes. Only one figure set per school is kept (no reproduction of full articles).
"""
from __future__ import annotations

import json
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "sources" / "raw" / "supp"
RAW.mkdir(parents=True, exist_ok=True)

PQ_URL = "https://poetsandquants.com/2026/09/10/total-cost-at-the-top-30-mba-programs-in-the-u-s/"
CA_URL = "https://www.clearadmit.com/real-numbers-of-mba-admissions/cost-of-mba-programs-in-the-u-s/"

# program_id, row label (must appear in the table row), tuition, fees, est one-year, est two-year, note
PQ = [
    ("kellogg-mba", "Kellogg", "$88,536", "$5,054", "$130,072", "$260,144", ""),
    ("hbs-mba", "Harvard", "$84,760", "$1,944", "$130,318", "$260,636", ""),
    ("disc-columbia-university-mba", "Columbia", "$93,908", "$6,783", "$143,030", "$286,060", ""),
    ("dartmouth-tuck-mba", "Tuck", "$87,536", "$6,150", "$135,331", "$270,662", ""),
    ("uva-darden-mba", "Darden", "$83,328", "$5,772", "$123,196", "$246,392", "P&Q marks Darden's other costs as estimated."),
    ("nyu-stern-mba", "Stern", "$92,658", "$2,040", "$140,668", "$281,336", ""),
    ("cornell-johnson-mba", "Johnson", "$88,934", "$2,200", "$127,278", "$254,556", ""),
    ("wharton-mba", "Wharton", "$87,970", "$5,038", "$135,441", "$270,882", ""),
    ("michigan-ross-mba", "Ross", "$83,946", "$494", "$116,300", "$232,600", ""),
    ("ucla-anderson-mba", "Anderson", "$82,734", "$2,105", "$137,951", "$275,902", "UCLA lists $82,734 as 'Estimated MBA Program Fees' rather than tuition."),
    ("mit-sloan-mba", "Sloan", "$89,692", "$2,620", "$144,325", "$288,650", ""),
    ("chicago-booth-mba", "Booth", "$89,976", "$4,744", "$132,449", "$264,898", ""),
    ("ut-mccombs-mba", "McCombs", "$61,214", None, "$85,889", "$171,778", "Tuition figure combines tuition and fees (not separated); likely the Texas-resident rate — check the non-resident rate on the official page."),
    ("berkeley-haas-mba", "Haas", "$90,191", "$2,564", "$138,921", "$277,842", ""),
    ("duke-fuqua-mba", "Fuqua", "$83,700", "$4,844", "$118,974", "$237,948", ""),
    ("cmu-tepper-mba", "Tepper", "$84,186", "$1,040", "$120,798", "$241,596", ""),
    ("yale-som-mba", "Yale", "$90,900", "$500", "$128,976", "$257,952", ""),
    ("vanderbilt-owen-mba", "Owen", "$76,700", "$2,926", "$113,537", "$227,074", ""),
    ("georgia-tech-scheller-mba", "Scheller", "$44,956", "$1,516", "$70,352", "$140,704", "Public university; the rate shown may be the in-state rate."),
    ("unc-kenan-flagler-mba", "Kenan-Flagler", "$74,192", None, "$103,612", "$207,224", "Tuition figure combines tuition and fees; may be the in-state rate."),
    ("emory-goizueta-mba", "Goizueta", "$79,200", "$2,452", "$120,096", "$240,192", ""),
    ("uw-foster-mba", "Foster", "$60,180", "$1,209", "$102,473", "$204,946", "Public university; the rate shown may be the in-state rate."),
    ("usc-marshall-mba", "Marshall", "$86,295", "$8,772", "$126,523", "$253,046", "P&Q marks USC's other costs as estimated."),
    ("georgetown-mcdonough-mba", "McDonough", "$75,016", "$54", "$115,171", "$230,342", ""),
    ("stanford-gsb-mba", "Stanford", "$89,187", "$843", "$140,940", "$281,880", ""),
    ("rice-jones-mba", "Rice", "$79,116", "$1,323", "$100,239", "$200,478", ""),
    ("notre-dame-mendoza-mba", "Mendoza", "$75,460", "$3,350", "$107,800", "$215,600", ""),
]
# program_id, row label, printed 2025-2026 figure, tuition-and-fees-only?
CA = [
    ("cmu-tepper-mba", "Tepper", "$116,428", False), ("disc-columbia-university-mba", "Columbia", "$137,571", False),
    ("cornell-johnson-mba", "Cornell", "$119,994", False), ("dartmouth-tuck-mba", "Tuck", "$135,329", False),
    ("duke-fuqua-mba", "Fuqua", "$114,952", False), ("emory-goizueta-mba", "Goizueta", "$115,722", False),
    ("georgetown-mcdonough-mba", "McDonough", "$111,487", False), ("hbs-mba", "Harvard", "$126,536", False),
    ("disc-indiana-university-mba", "Kelley", "$83,940", False), ("mit-sloan-mba", "MIT Sloan", "$138,310", False),
    ("kellogg-mba", "Kellogg", "$128,852", False), ("nyu-stern-mba", "Stern", "$135,840", False),
    ("vanderbilt-owen-mba", "Owen", "$111149", False), ("rice-jones-mba", "Rice", "79,116", True),
    ("stanford-gsb-mba", "Stanford", "$135,771", False), ("berkeley-haas-mba", "Haas", "$133,655", False),
    ("ucla-anderson-mba", "Anderson", "$133,655", False), ("chicago-booth-mba", "Booth", "$129,403", False),
    ("michigan-ross-mba", "Ross", "$111,725", False), ("minnesota-carlson-mba", "Carlson", "$71,791.88", True),
    ("unc-kenan-flagler-mba", "Kenan-Flagler", "$102,960", False), ("ut-mccombs-mba", "McCombs", "$122,428", False),
    ("uva-darden-mba", "Darden", "$121,275", False), ("uw-foster-mba", "Foster", "$100,044", False),
    ("wharton-mba", "Wharton", "$132,404", False), ("yale-som-mba", "Yale", "$123,936", False),
]
# USC's 2025-26 Clear Admit cell carries conflicting footnotes (^ and **), so it is deliberately not imported.

num = lambda s: float(s.replace("$", "").replace(",", ""))  # noqa: E731
pq = []
for pid, label, tu, fee, one, two, note in PQ:
    base = {"program_id": pid, "row_label": label, "source_url": PQ_URL, "publisher": "Poets&Quants", "source_type": "secondary",
            "retrieved_on": "2026-10-23", "period": "2026-2027"}
    pq.append({**base, "field": "tuition", "value": num(tu), "printed": tu, "unit": "USD", "period_basis": "annual", "value_kind": "reported",
               "notes": note or "Tuition as published by the school, reported by Poets&Quants."})
    if fee:
        pq.append({**base, "field": "mandatory_fees", "value": num(fee), "printed": fee, "unit": "USD", "period_basis": "annual",
                   "value_kind": "reported", "notes": "Required fees as published by the school, reported by Poets&Quants."})
    pq.append({**base, "field": "est_annual_cost", "value": num(one), "printed": one, "unit": "USD", "period_basis": "annual", "value_kind": "estimate",
               "notes": "Poets&Quants projection: tuition + mandatory fees + estimated living and other costs for one year. Not a bill." + (f" {note}" if note else "")})
    pq.append({**base, "field": "est_two_year_cost", "value": num(two), "printed": two, "unit": "USD", "period_basis": "full_program", "value_kind": "estimate",
               "notes": "Poets&Quants projection: the one-year estimate doubled (no inflation adjustment)."})
ca = []
for pid, label, fig, tf_only in CA:
    ca.append({"program_id": pid, "row_label": label, "source_url": CA_URL, "publisher": "Clear Admit", "source_type": "secondary",
               "retrieved_on": "2026-10-23", "period": "2025-2026", "period_basis": "annual", "unit": "USD", "printed": fig, "value": num(fig),
               "field": "tuition_and_fees" if tf_only else "reported_cost_of_attendance", "value_kind": "reported",
               "notes": ("Clear Admit marks this figure as tuition and fees only." if tf_only else
                         "Cost of attendance for a single, non-resident student living off campus, compiled by Clear Admit. One academic year older than 2026-27 figures.")})
(RAW / "secondary_poetsandquants_2026.json").write_text(json.dumps(pq, indent=1), encoding="utf-8")
(RAW / "secondary_clearadmit_2025.json").write_text(json.dumps(ca, indent=1), encoding="utf-8")
print(len(pq), "P&Q records;", len(ca), "Clear Admit records")
