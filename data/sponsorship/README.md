# Employer H-1B evidence (U.S. DOL LCA disclosure data)

**What it is:** historical H-1B Labor Condition Application (LCA) filings by employers that a program's **official employment report** says hired its graduates.

**What it is not:** an LCA is filed by an employer for a position. It is not a visa approval, and never a promise that an employer will sponsor any particular person or role. Wherever this data appears, the app shows:

> Historical H-1B filings by this employer. Not a guarantee of sponsorship. U.S. work-authorization rules change; confirm with official sources and the school's international student office. Not legal advice.

## Files
| File | Committed? | What |
|---|---|---|
| `raw/LCA_Disclosure_Data_FY2025_Q1..Q4.xlsx` | **No** (git-ignored, about 420 MB) | Official DOL files |
| `lca_filtered.csv` | Yes (~260 KB) | One row per employer + occupation + metro + fiscal year, with filings, worker positions and median annual wage. It is also the **small test dataset**. |
| `provenance.json` | Yes | Source page and file URLs, SHA-256 hashes, case counts and decision-date ranges per file, fiscal-year coverage, download date, and the filters |
| `employer_aliases.csv` | Yes | The **reviewed** exact-match alias table, one row per name variant, each with a review note |
| `unmatched_review.md` | Yes | School-listed names deliberately left unmatched, and why |

## Rebuild from the official files
1. Open https://www.dol.gov/agencies/eta/foreign-labor/performance, go to **LCA Programs (H-1B, H-1B1, E-3)**, and download `LCA_Disclosure_Data_FY2025_Q1.xlsx`, `…Q2.xlsx`, `…Q3.xlsx` and `…Q4.xlsx`. dol.gov blocks automated downloads, so use a browser.
2. Save them in `data/sponsorship/raw/`.
3. Install the dev-only packages and run the build (about 15 minutes):
   ```
   .venv\Scripts\pip install -r requirements-dev.txt
   .venv\Scripts\python scripts\build_sponsorship.py
   ```

Each DOL quarterly file holds **only that quarter's decisions**; the script checks this, and `provenance.json` records the decision-date range of each file. The current build uses all four quarters of FY2025 (October 1, 2024 to September 30, 2025): 596,552 cases, of which 552,036 were certified.

## Stated assumptions (also in `scripts/build_sponsorship.py`)
- **Visa class and status:** H-1B only, and `CASE_STATUS == "Certified"` only.
- **Occupations:**

  | Occupation | Definition |
  |---|---|
  | Management consulting | SOC 13-1111 |
  | Corporate finance / strategy | SOC 13-2051, 13-2054, 11-3031, plus 13-1199 when the job title mentions strategy |
  | Product management | No SOC code exists, so: job title "product manager/management/lead/owner/director" (not "product marketing") in SOC major groups 11, 13 or 15 |

- **Metros:**
  - Boston, Seattle and Houston: those cities in MA, WA and TX respectively.
  - New York: Manhattan only.
  - San Francisco Bay Area: a fixed list of 34 California cities.
- **Wage:** annualized `WAGE_RATE_OF_PAY_FROM`; median per group.
- **Employer matching:** exact, after trimming, collapsing spaces and ignoring case, through `employer_aliases.csv`. There is no fuzzy matching; a name without a reviewed alias stays unmatched.
