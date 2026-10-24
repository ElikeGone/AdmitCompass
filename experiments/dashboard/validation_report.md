# Step 10 — Dashboard evidence & affordability validation (2026-10-23)

Source of every displayed value: `GET /api/dashboard/demo` = saved run `20261023T180104Z` (report id `ae6f197e0040`) + current evidence store. All calculations are in `backend/app/tools/dashboard.py` (no model calls). Automated checks: `tests/test_dashboard.py` (10 tests).

## Affordability (budget $135,000 per academic year, from the fictional profile)

| Program | Verified COA (period) | Tuition (period) | Gap = budget − COA | Dashboard shows |
|---|---|---|---|---|
| MIT Sloan | not verified | $91,892 (2026-2027) | — | "Not enough comparable data" (tuition excludes living costs) |
| Chicago Booth | $132,449 (2026-2027) | $89,976 (2026-2027) | +$2,551 | Headroom $2,551 |
| Duke Fuqua | $118,974 | verified | +$16,026 | Headroom $16,026 |
| Yale SOM | $128,976 | verified | +$6,024 | Headroom $6,024 |

Gaps were checked against the store by `test_gap_is_budget_minus_coa`. Edge cases were tested with synthetic inputs:
- zero gap → "within", with a "no headroom" note;
- negative gap (−$15,000) → "shortfall";
- a total-program budget → not compared;
- no budget → not compared;
- a non-academic-year cost period → not compared.

No scholarships are shown or assumed.

## International feasibility
- **STEM:** verified as designated for all 4 programs, with the official scope text and source link.
- **International outcomes** (corrected during the homepage milestone; the first version of this report wrongly said none of the 4 had a figure):
  - Yale SOM has an official figure: international students' median base salary of $175,000, Class of 2025, shown with its source.
  - Chicago Booth's stored fact is a sourced *statement* that no international-specific statistics exist. It is now shown as "No outcome figure published", where it used to be labeled "Official".
  - MIT Sloan and Duke Fuqua have nothing on file and show "Not published".
  - Rule: a verified value counts as a figure only if it states a % or $ statistic. This is tested by `test_international_figure_vs_statement`.
- **Sponsorship:** "Unknown" for all 4, because there is no employer-specific evidence.
- **The STEM ≠ sponsorship note** is always shown.
- **Unknown-STEM handling:** tested synthetically.

## Program fit
- **Career fit labels and rationale** come from the saved run.
- **"Supported by evidence"** lists only `verified_fact` claims whose evidence ids resolve in the store (tested).
- **Unknown facts** are listed per program.
- **No percentages or admission odds** are shown.

## Pathway
- **Strengths:** 5 profile facts, labeled "From your profile".
- **Gaps:** 7 gaps from the Strategy Planner, labeled "AI-inferred".

## Workspace and deadlines
- **Tasks:** 40 weekly tasks, each in exactly one roadmap phase: 12 in Weeks 1-3, 16 in Weeks 4-7, 12 in Weeks 8-10, and 0 in the post-submission phase.
- **Task ids** are stable (`w{week}-{index}`).
- **Deadlines:** none are verified in the store for these 4 programs, so all show "Not checked yet — confirm on the official admissions page". No dates are invented.

## Browser interaction results (preview pane plus headless Edge)

| Check | Result |
|---|---|
| Switching programs updates the fit, affordability and international sections | pass (values listed above) |
| Mark complete | pass: 1/40, stored in `ac-workspace-ae6f197e0040` |
| Undo | pass: back to 0/40 |
| Reset (with confirmation), then undo the reset | pass: 0/40, then 2/40 restored |
| Reload persistence | pass |
| Invalid stored entries are ignored | pass: `bogus` and non-true values dropped |
| Next task highlighted and moves forward | pass |
| Buttons are focusable and have descriptive aria-labels | pass |
| Horizontal overflow | none at 375, 768, 1024 or 1440 (an overflowing button bug was found and fixed: a class name collided with `.sm`) |
| Light and dark themes | both render |

## Known limitation found during validation
In the saved run, the MIT **model-written** fit rationale says verified tuition of $91,892 is "within the annual budget". That compares tuition with a total budget, which the dashboard's own code refuses to do. The text is shown verbatim, labeled "AI inference", and the deterministic affordability card next to it correctly says "Not enough comparable data". Changing the saved run's text would falsify it, so it is left as it is and disclosed here.
