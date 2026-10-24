"""Write the REVIEWED alias table (decisions made by reading experiments/sponsorship/alias_candidates.txt).

Every row is a human decision recorded with a note; there is no fuzzy matching. Re-run after editing:
    .venv/Scripts/python scripts/make_aliases.py
"""
import csv
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "sponsorship" / "employer_aliases.csv"
SAME = "Same firm's U.S. filing entity (reviewed 2026-10-23)."
SUB = "U.S. subsidiary of the same firm that files LCAs separately (reviewed 2026-10-23)."
# canonical -> (school names as printed in verified lists, LCA names as filed, note)
TABLE = {
    "Accenture": (["Accenture", "Accenture Strategy"], ["Accenture LLP"], SAME + " 'Accenture Strategy' is Accenture's strategy practice; it files under Accenture LLP."),
    "Adobe": (["Adobe, Inc.", "Adobe"], ["Adobe Inc."], SAME),
    "Airbnb": (["Airbnb"], ["AIRBNB, INC."], SAME),
    "AlixPartners": (["AlixPartners"], ["AlixPartners, LLP", "AlixPartners, LLC"], SAME),
    "Alvarez & Marsal": (["Alvarez & Marsal"], ["Alvarez & Marsal Consumer and Retail Group, LLC", "ALVAREZ & MARSAL CONSUMER AND RETAIL GROUP, LLC",
                                                 "Alvarez & Marsal Private Equity Performance Improvement Group, LLC", "Alvarez & Marsal Valuation Services, LLC",
                                                 "Alvarez & Marsal Public Sector Services, LLC", "Alvarez & Marsal Transaction Advisory Group, LLC",
                                                 "ALVAREZ & MARSAL DISPUTES AND INVESTIGATIONS, LLC", "Alvarez & Marsal Healthcare Industry Group, LLC"], SUB),
    "Amazon": (["Amazon", "Amazon.com, Inc."], ["Amazon.com Services LLC", "AMAZON.COM SERVICES LLC", "Amazon Development Center U.S., Inc.",
                                                "AMAZON DEVELOPMENT CENTER U.S., INC.", "Amazon Web Services, Inc.", "AMAZON WEB SERVICES, INC.",
                                                "Amazon Web Services Inc", "Amazon Payments, Inc.", "Amazon Data Services, Inc", "Amazon Advertising LLC",
                                                "AMAZON ADVERTISING LLC", "Amazon Capital Services, Inc."], SUB),
    "Apple": (["Apple"], ["Apple Inc."], SAME),
    "Arthur J. Gallagher": (["Arthur J Gallagher"], ["Arthur J. Gallagher Service Company, LLC"], SAME),
    "Bain & Company": (["Bain & Company", "Bain & Company, Inc.", "Bain and Co"], ["BAIN & COMPANY, INC."], SAME + " Bain Capital is a different firm and is NOT mapped."),
    "Bank of America": (["Bank of America", "Bank of America Corporation"], ["BANK OF AMERICA N.A.", "BANK OF AMERICA CORPORATION"], SUB),
    "Barclays": (["Barclays", "Barclays PLC"], ["Barclays Capital Inc.", "Barclays Services Corp.", "Barclays Bank PLC"], SUB),
    "BMO Financial Group": (["BMO Financial Group"], ["BMO Capital Markets Corp.", "BMO Bank N.A."], SUB),
    "Boston Consulting Group": (["BCG", "Boston Consulting Group", "Boston Consulting Group, Inc.", "The Boston Consulting Group, Inc."],
                                ["Boston Consulting Group, Inc."], SAME + " 'BCG GLASS INDUSTRY INC.' is unrelated and NOT mapped."),
    "Capital One": (["Capital One Financial Corp", "Capital One"], ["Capital One Services, LLC", "Capital One, National Association"], SUB),
    "Citigroup": (["Citi", "Citigroup Inc.", "Citigroup, Inc."], ["Citigroup Global Markets Inc.", "Citigroup Energy Inc.", "Citi Ventures Inc."], SUB),
    "Deloitte Consulting": (["Deloitte Consulting", "Deloitte Consulting LLP"], ["Deloitte Consulting LLP"],
                            SAME + " Deloitte & Touche (audit), Deloitte Tax and other Deloitte entities are NOT mapped: the school names the consulting firm."),
    "Evercore": (["Evercore Partners Inc."], ["EVERCORE PARTNERS SERVICES EAST LLC"], SUB),
    "Goldman Sachs": (["Goldman Sachs", "Goldman Sachs Group Inc.", "The Goldman Sachs Group, Inc."],
                      ["GOLDMAN SACHS & CO. LLC", "GOLDMAN SACHS BANK USA", "GOLDMAN SACHS SERVICES LLC", "Goldman Sachs Wealth Services, L.P."],
                      SUB + " J. Goldman & Co. is a different firm and is NOT mapped."),
    "Google": (["Google"], ["Google LLC"], SAME),
    "Jefferies": (["Jefferies Group, Inc."], ["Jefferies LLC"], SUB),
    "JPMorgan Chase": (["JPMorgan Chase & Co.", "JP Morgan Chase & Co."], ["JPMorgan Chase & Co."], SAME),
    "Kearney": (["Kearney"], ["A.T. Kearney, Inc."], SAME),
    "L.E.K. Consulting": (["L.E.K. Consulting"], ["L.E.K Consulting, LLC", "L.E.K. Consulting LLC", "LEK Consulting LLC"], SAME),
    "McKinsey & Company": (["McKinsey & Company", "McKinsey & Company, Inc.", "McKinsey & Co"],
                           ["McKinsey & Company, Inc. United States", "MCKINSEY & COMPANY, INC. UNITED STATES", "McKinsey & Company, Inc., United States"], SAME),
    "Microsoft": (["Microsoft", "Microsoft Corporation"], ["Microsoft Corporation"], SAME),
    "Morgan Stanley": (["Morgan Stanley"], ["Morgan Stanley & Co., LLC", "Morgan Stanley Services Group Inc.", "Morgan Stanley & Co, LLC",
                                            "Morgan Stanley Investment Management Inc.", "Morgan Stanley Bank N.A.", "Morgan Stanley Fund Services Inc.",
                                            "Morgan Stanley Services Group, Inc.", "Morgan Stanley Smith Barney LLC", "Morgan Stanley & Co, LLC.",
                                            "Morgan Stanley & Co. LLC", "Morgan Stanley Private Bank NA", "Morgan Stanley Private Bank, NA"], SUB),
    "NVIDIA": (["nVidia", "NVIDIA Corporation"], ["NVIDIA Corporation"], SAME),
    "Roland Berger": (["Roland Berger LLC"], ["Roland Berger LP"], SAME),
    "IBM": (["IBM", "International Business Machines Corporation"], ["IBM Corporation"], SAME + " (reviewed 2026-10-24)"),
    "Fidelity Investments": (["Fidelity Investments"], ["FMR LLC", "FMR LLC d/b/a Fidelity Investments", "F-Prime, Inc. d/b/a Fidelity Investments",
        "Fidelity Brokerage Services LLC d/b/a Fidelity Investments", "Fidelity Global Brokerage Group, Inc. d/b/a Fidelity Investments",
        "Fidelity Investments Institutional Operations Company d/b/a Fidelity Investments", "Fidelity Management & Research Company",
        "Fidelity Management & Research Company LLC", "Fidelity Management & Research Company LLC d/b/a Fidelity Investments",
        "Fidelity Technology Group, LLC", "Fidelity Technology Group, LLC d/b/a Fidelity Investments",
        "Fidelity Workplace Investing LLC d/b/a Fidelity Investments", "National Financial Services LLC d/b/a Fidelity Investments"],
        SUB + " FMR LLC is Fidelity's parent; every other row files 'd/b/a Fidelity Investments' or is a Fidelity-named entity (reviewed 2026-10-24)."),
    "Palantir": (["Palantir"], ["PALANTIR TECHNOLOGIES INC."], SAME + " (reviewed 2026-10-24)"),
    "TikTok": (["TikTok"], ["TikTok Inc.", "TikTok U.S. Data Security Inc."], SUB),
}
UNMATCHED_NOTE = {  # recorded for the audit trail; these have NO alias row, so they stay unmatched
    "EY-Parthenon": "Strategy unit of EY; mapping it to all Ernst & Young U.S. LLP filings (mostly audit/tax) would overstate. Left unmatched.",
    "PwC Strategy&": "Strategy& can't be tied to a specific PwC filing entity. Left unmatched.",
    "Bessemer Trust Company": "Only candidate is Bessemer Venture Partners, a different firm. Left unmatched.",
    "Altas Cumbres": "Only candidate is Altas Partners, a different firm. Left unmatched.",
    "Johnson & Johnson (MIT)": "Only candidate is Johnson Controls, a different firm. Left unmatched.",
    "NextEra Energy (MIT)": "Only candidates are unrelated energy companies. Left unmatched.",
    "Biogen, Formlabs, McMaster-Carr, Moderna, Sanofi, Verizon (MIT)": "No filings in the three target occupations and five cities. Unmatched (no rows).",
}
with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["canonical_employer", "alias", "alias_source", "reviewed_note"])
    for canon, (school, lca, note) in TABLE.items():
        for s in school:
            w.writerow([canon, s, "school_evidence", "School-printed name; same firm as canonical (reviewed 2026-10-23)."])
        for n in lca:
            w.writerow([canon, n, "lca", note])
(OUT.parent / "unmatched_review.md").write_text(
    "# Reviewed but deliberately unmatched employer names\n\n" + "\n".join(f"- **{k}**: {v}" for k, v in UNMATCHED_NOTE.items())
    + "\n\nAny school-listed name not in `employer_aliases.csv` is left unmatched by design (no fuzzy matching).\n", encoding="utf-8")
print(sum(len(s) + len(l) for s, l, _ in TABLE.values()), "alias rows,", len(TABLE), "employers")
