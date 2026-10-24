# Step 14 — MBA research engine and data completeness (2026-10-23)

## Pipeline
1. **Collect.** Raw records go into `data/sources/raw/supp/`.
   - Secondary sources: transcribed by `scripts/make_secondary_raw.py`, keeping each figure exactly as printed.
   - Official pages: 3 research subagents, only on each school's own domain.
2. **Validate independently** with `scripts/build_supplementary.py`. It is deterministic and treats nothing from the collectors as trusted.
   - **Fetching:** one polite fetch per page with an honest user agent. It honors robots.txt, including P&Q's 10-second crawl delay, and never bypasses blocks. Page snapshots are cached in `data/sources/cache/supp/`.
   - **Identity checks:**
     - official records must come from the program's own official domain;
     - each secondary figure must appear in the same table row as the school's name.
   - **Value checks:**
     - the number must be on the live page, next to a word that says what it is ("class", "GMAT", "fee"…), so a stray "367" elsewhere doesn't count;
     - every deadline date must appear;
     - scholarship wording must match.
   - **Results** are logged per record in `experiments/research/supplementary_validation.csv`.
3. **Store.** Results go to `data/programs/supplementary.json`, validated by `SuppFact` in `backend/app/schemas/supplementary.py`. Each fact records:
   - program and field, value and unit, period and its basis (annual, whole program, cohort or cycle);
   - source URL and publisher, whether the source is official or secondary, and whether the value is published, reported or an estimate;
   - retrieval date, status, what the validator checked, and comparability notes.
4. **Rules.**
   - The core evidence store (which the agents use) is never overwritten.
   - A secondary source can never supply an official cost of attendance, and an official value can never be an estimate (both enforced by the schema).
   - Only **verified** records are shown as values; everything else appears as a research gap with its reason.

## Results

| | Count |
|---|---:|
| Verified facts | **176** |
| Programs with new verified facts | **29 of 30** (only Texas A&M Mays isn't covered by either secondary source) |
| Official facts (school pages) | **44** across 10 programs |
| Secondary figures reported by a third party | **78** (P&Q-reported tuition and fees; Clear Admit's compiled 2025–26 cost of attendance) |
| Secondary estimates | **54** (P&Q estimated one-year and two-year costs, 2026–27) |
| Not verified | 28: 22 not found, 4 unverified (the value isn't on the live page), 2 blocked |

**Official facts by field:**

| Field | Count |
|---|---:|
| Class size | 8 |
| Deadlines for the 2026–27 cycle | 8 |
| International % | 7 |
| Scholarship statements | 6 |
| Mandatory fees | 4 |
| Cost of attendance | 4 |
| Average GMAT | 4 |
| Median GMAT | 3 |

The 10 programs with official facts: Yale, HBS, MIT, Booth, Duke, Rice, Wharton, Tuck, Haas and Kellogg.

**Secondary figures by field:**

| Field | Source | Count |
|---|---|---:|
| Estimated one-year cost | P&Q | 27 |
| Estimated two-year cost | P&Q | 27 |
| Tuition as reported | P&Q | 27 |
| Fees as reported | P&Q | 25 |
| Tuition and fees combined | P&Q | 2 |
| Cost of attendance, 2025–26 | Clear Admit | 24 |

### The MIT example
- **Official tuition and mandatory fees:** $91,892 for 2026–27 (core store; MIT says the $2,200 fee is included in that figure).
- **P&Q estimated one-year cost:** $144,325 for 2026–27, an estimate.
- **Clear Admit compiled cost of attendance:** $138,310 for 2025–26, one year older.

All three are stored and shown as separate labeled lines, explained as measuring different things. The dashboard still says there is no official total cost, and adds a labeled estimate: a $9,325 shortfall against the $135,000 budget.

### Honest corrections the validator made
- **Booth and Duke mandatory fees:** the collector summed several fee lines ($4,744 and $4,844). Those totals don't appear on the official pages, so they stay **unverified**; P&Q's reported fees are shown instead and labeled.
- **Haas median GMAT and international %:** not found on the live page, so **unverified**.
- **Public schools:** P&Q's tuition for McCombs, UNC, Georgia Tech and Foster may be the in-state rate. Those estimates stay in the detailed lines with that caveat but are **not** used as card headlines or budget comparisons. Cards show Clear Admit's non-resident compiled cost where it exists, for example McCombs at $122,428 for 2025–26.
- **USC:** Clear Admit's 2025–26 cell has conflicting footnotes, so it was not imported.

## Unresolved fields (shown in each program's "Open research questions")
- **MIT Sloan:** official cost of attendance (not on the financing pages checked); class profile figures (loaded with JavaScript, so not readable).
- **Rice:** official cost of attendance and 2026–27 deadlines (only "Round 2: January 6" is printed, with no year); median GMAT.
- **Duke:** median and average GMAT (only a GMAT Focus range is published).
- **Stanford, Darden, Kellogg:** class profile and deadline pages returned 404s or JavaScript-only content.
- **Tuck:** deadlines page empty.
- **Scholarships:** not researched within the timebox for Wharton, Kellogg, Stanford, Tuck, Haas and Darden.
- **The other 16 programs:** official class profile, scholarships and deadlines were not researched in this timebox. They have secondary cost coverage only.

## Blocked or inaccessible sources
- **U.S. News rankings page:** timed out for automated clients (WebFetch and the script), so it was recorded as inaccessible and no ranking data was imported. Rankings are not used as evidence of career fit.
- **Michigan Ross and NYU Stern official pages:** HTTP 403 (blocked), recorded as blocked.
- **Poets&Quants and Clear Admit:** accessible, and robots.txt permits these article paths. For each school, only the figures listed above were stored, with attribution and a link. No articles or full tables were reproduced.

## Data-quality caveats
- **Scale and cohort differences:**
  - HBS's median GMAT (685) and Tuck's average (682) may be on the GMAT Focus scale, which isn't comparable with classic-scale figures.
  - Rice's class profile averages its 2026–2028 cohorts.
  - Wharton's figures are for the Class of 2026.

  The notes are kept on each fact and shown in the UI.
- **Uncertain round labels:**
  - Kellogg's deadlines come from a general admissions page, so it's unconfirmed that they apply only to the full-time MBA.
  - The "Class of 2029" round labels are inferred from the cycle dates.
