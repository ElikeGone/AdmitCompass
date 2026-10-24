# Rubric Tracker

Official source: [docs/rubric/official_requirements.md](rubric/official_requirements.md). Total 100 points.
Status values: `pending` / `in progress` / `verified` (verified = the evidence file was opened and checked).
**Evidence rule:** any row missing its required evidence is capped at half points.

Last inspected: 2026-10-23 (Step 9B: 28 programs with sourced facts, link audit, colour; 170 tests). Earlier, Step 10: 4.0 visual reset of homepage + Explore, `deliverables/screenshots/v4/`, 155 tests). Earlier, Step 9: homepage + Explore v3, screenshots in `deliverables/screenshots/v3/`, 154 tests). Earlier, Step 8: v2 redesign, discovery tier with 24 programs, 151 tests, `deliverables/screenshots/v2/`). Earlier, Step 7: safety matrix 24/24, tokenomics + optimization, performance; see `docs/evidence_index.md`). Step 6: web app, 8 screenshots. Earlier, Step 5: complete run `20261023T180104Z`, audit ok. Earlier in Step 5: Added agents and orchestrator, 78 mocked tests, `experiments/agent_runs/` (3 real attempts: 2 rejected at request 1, 1 stopped by the budget; no complete trace yet). Earlier, Step 4: Added: `data/programs/programs.json`, `experiments/source_audit.json` (49/78 fields verified), `tests/test_programs.py` (48 tests total pass). Earlier, Step 3: Supporting evidence so far: `experiments/smoke_test/` (1 real call, real token counts) and `tests/test_foundation.py` (19 passing). No rubric row is complete yet.

| # | Criterion | Pts | Required evidence | Implementation plan | Evidence location | Status |
|---|---|---|---|---|---|---|
| 1 | Novelty + real-world value | 21 | Clear twist vs. ChatGPT/existing tools; evidence it helps real people (aims at Tier 3) | Career-first matching + evidence-gated STEM/sponsorship + Skeptic + two-tier discovery (verified vs needs-verification); competitor test of same prompts in ChatGPT | `experiments/competitor_comparison/`, report §3, `data/discovery/` | in progress (evidence-gated dataset; **employer-specific H-1B evidence from DOL FY2025 LCA data** joined to official employer lists, `data/sponsorship/`; competitor test not run) |
| 2 | App works | 15 | End-to-end run on demo profiles without errors; real outputs | 4-agent pipeline, FastAPI, UI; golden-profile tests | `tests/`, `deliverables/screenshots/` | in progress (**live run from the web UI done**: Ghana fixture, 12 requests, completed; screenshots in `deliverables/screenshots/final/`) |
| 3 | Teaching staff can run it | 5 | Fresh clone → running in ≤10 min; `.env` loaded from repo then parent | `.env` loader, one-command start, fresh-clone dry run timed | `experiments/fresh_clone_test.md` | in progress (**fresh-clone scripts PASS**: Windows 122 s, bash/Python 3.11 103 s to `/health`, `.env` one level above; to re-run with the GitHub URL after pushing) |
| 4 | Look + feel | 10 | Polished UI screenshots; clear evidence cards & trace | Single-page app: intake → results tabs → evidence → trace | `deliverables/screenshots/v2/` | in progress (v2 hybrid redesign after real product feedback; 9 genuine screenshots incl. mobile; browser-tested at 1024/375/320 px; no formal user test yet) |
| 5 | Motivation + what is new | 8 | Who has the problem, cost in money/time/frustration (sourced); alternatives incl. ChatGPT compared | Cited stats + competitor comparison table | report §2–3, `experiments/competitor_comparison/` | pending |
| 6 | Agent design | 10 | Roles, tools, handoffs diagram, models + why, one real step-by-step run with screenshots | Trace viewer + exported trace JSON | report §4, `experiments/agent_runs/` | in progress (real traces + **agent diagram** `deliverables/diagrams/agent_diagram.{mmd,svg,png}`; report section still to write) |
| 7 | Tokenomics | 8 | **Measured** input/cached/output tokens per run; cost per run, per user/month, at 100 & 10k users; cost-cut experiment + trade-off | Token logger from API `usage`; baseline vs optimized runs | `experiments/tokenomics/` | in progress (**clean Task 3 runs with Portkey cache force-refresh**, per-agent/per-run tokens in `experiments/tokenomics/clean_runs_analysis.md`; earlier: real per-agent tokens + retry overhead + cache analysis; cost-cut experiment −29% requests / −30% est. tokens with quality preserved; **price unknown → hypothetical $ only**; no fresh real run of the optimized path) |
| 8 | Safety | 8 | Injection/misuse, malfunctions, overspending covered; **≥1 defense shown working** | Injection tests on intake & evidence text; schema/claim validator; per-run cost cap | `tests/test_safety.py`, `experiments/safety/` | in progress (**26/26 red-team scenarios pass** incl. S25 'Will McKinsey sponsor me?' and S26 injection in employer names, `experiments/safety/safety_test_matrix.md`; 6 vulnerabilities found and fixed; real budget stop + fail-closed runs on file) |
| 9 | Impact + metrics | 5 | Quantified benefit with sources; **real user quote or before/after time** | Timed baseline (manual research vs app) + 1–3 real-user sessions | `experiments/user_testing/`, `docs/user_test_protocol.md` | pending (protocol + form ready; **0 sessions**; local performance metrics exist) |
| 10 | Report design | 2 | Self-contained `report.html`, 10–15 printed pages, sections in exact order, images embedded | Build script embeds images as base64 | `deliverables/report.html` | pending |
| 11 | Slides content | 6 | ≤10 slides covering suggested order | reveal.js deck from report content | `deliverables/slides.html` | pending |
| 12 | Slides design | 2 | Clean, self-contained, images embedded, reveal.js CDN | Same embed script | `deliverables/slides.html` | pending |

## Non-graded but required submission items
| Item | Location | Status |
|---|---|---|
| Public GitHub repo (or private + `zlisto`) | — | in progress (local git repo, first commit `8985bf2`; not pushed yet) |
| README.md with step-by-step setup | `README.md` | done (grader README; history moved to `docs/CHANGELOG.md`; steps verified by the fresh-clone scripts) |
| `.env.example`, no real values | `.env.example` | done (every setting the code reads, plus prices with source notes) |
| Small test dataset + switch instructions | `data/` | done (`data/sponsorship/lca_filtered.csv` + rebuild instructions in `data/sponsorship/README.md`) |
| Optional 2–3 min demo video | `deliverables/` | pending |

- 2026-10-23 Step 10: Career Intelligence dashboard added (deterministic API, 10 new tests, 181 total); see experiments/dashboard/validation_report.md.

## Final-sprint task log
- 2026-10-23 **Task 1 — Employer sponsorship evidence: done.**
  - **Data:** DOL OFLC FY2025 LCA disclosure, all four quarters (596,552 cases), filtered to `data/sponsorship/lca_filtered.csv` (3,000 rows, 7,877 certified H-1B filings) with `provenance.json`. Raw files are git-ignored.
  - **Employer evidence:** official hiring-employer lists for Yale, Booth, Fuqua and Tuck, validated against the live pages (`sx-...` ids). MIT, HBS and Rice stay unknown, with reasons. A reviewed alias table maps 29 employers through 120 exact aliases; unmatched names stay unmatched.
  - **Agents:** new tool `get_sponsorship_evidence` with `lca-...` evidence ids, for the Evidence Analyst and the Skeptic.
  - **Guarantee blocking:** a new `sponsorship_guarantee` rule is shared by the agents and the copilot.
  - **UI:** the required note shows on the dashboard and in Explore.
  - **Tests:** 259 passed, 1 skipped; safety matrix 26/26. Screenshot: `deliverables/screenshots/final/task1_h1b_history_dashboard.jpg`.
- 2026-10-23 **Task 2 — Demo fixtures: code done; shortlist comparison confirmed with the Task 3 live runs.**
  - **Fixtures:** `fixture-audit-consulting-ghana` and `fixture-domestic-tech-us` (both fictional).
  - **Detailed-only shortlist:** fictional demo runs use only the 5 programs with "detailed" evidence (setting `AC_DEMO_DETAILED_ONLY`, on by default). Real users get all 28.
  - **International layer:** STEM status and H-1B evidence appear only when `needs_us_work_authorization` isn't false.
  - **Tests:** 263 passed, 1 skipped.
- 2026-10-24 **Task 3 — Fresh live runs and token evidence: done.**
  - **Clean runs:** two live four-agent runs with the header `x-portkey-cache-force-refresh: true` (setting `PORTKEY_CACHE_FORCE_REFRESH`):
    - `20261024T020115Z_fixture-audit-consulting-ghana`: completed, 13 requests;
    - `20261024T020259Z_fixture-domestic-tech-us`: 11 requests; 3 sponsorship-status corrections caused by a rule I fixed right after.
  - **Tokenomics:** `experiments/tokenomics/clean_runs_analysis.{md,json}` from `analyze_clean_runs.py` (per agent and per run; cost per run, per user per month, at 100 and 10,000 users).
  - **Prices:** no official price found, so only labeled hypothetical scenarios. The price settings, with source notes, are in `.env.example`.
  - **Live UI run:** completed in 12 requests (shortlist MIT and Duke). Screenshots: `deliverables/screenshots/final/task3_live_run_monitor.jpg`, `task3_live_results_dashboard.jpg`, `task3_live_results_international_ghana.jpg`.
  - **Tests:** 263 passed, 1 skipped.
- 2026-10-24 **Task 4 — Run-it-anywhere hardening: done.**
  - **Settings:** `.env.example` lists every setting the code reads; the unused HOST/PORT entries were removed.
  - **Python versions:** one 3.12-only f-string fixed. The full suite passes on Python 3.10, 3.11 and 3.14; the true minimum is 3.10.
  - **Fresh-clone scripts:** `scripts/fresh_clone_test.ps1` and `.sh` both PASS (122 s and 103 s); results are in `experiments/fresh_clone_test.md`. There's no git remote yet, so they copied the working tree; re-run them with the repo URL after pushing.
  - **README:** rewritten for graders; the development history moved to `docs/CHANGELOG.md`.
  - **Tests:** 263 passed, 1 skipped.
- 2026-10-24 **Task 5 — Trim scope: done.**
  - **Accounts:** behind `AC_ENABLE_ACCOUNTS`, off by default. The APIs return 404 and the navigation entries are hidden; the account tests run with it on, and a new test checks the default.
  - **Ask AI:** works with the live key (`scripts/copilot_live_check.py`, `experiments/copilot/live_check.md`: 3 questions, all answered, 4–9 s each), so it stays enabled.
    - Its model calls now count against the per-run caps for each conversation; the 429 response was verified with a mocked model.
    - Token usage is logged to `logs/copilot_usage.jsonl` (no question or answer text).
  - **Copilot bugs fixed** (found in the live test): `lca-` citations, readable fallbacks for H-1B facts, a named employer ("McKinsey") now retrieves its own filings, and placeholder brackets are removed.
  - **Tests:** 266 passed, 1 skipped.
- 2026-10-24 **Task 6 — Report evidence prep: done (report not written, by instruction).**
  - **Agent diagram:** `deliverables/diagrams/agent_diagram.mmd`, `.svg` and `.png` (orchestrator, 4 agents, 6 tools incl. `get_sponsorship_evidence`, handoffs, the Skeptic's ≤1 revision, grounding checks, data stores). Rendered with Mermaid 11 via `scripts/render_diagram.ps1`.
  - **Competitor kit:** `experiments/competitor_comparison/` with the exact ChatGPT prompts for both fixtures, a scoring template, and a placeholder comparison of 6 tools. Only AdmitCompass cells are filled, each with its evidence; the owner runs ChatGPT.
  - **Evidence index:** `docs/evidence_index.md` maps every rubric row to its evidence files, screenshots and open gaps.
  - **Tests:** 266 passed, 1 skipped.
- 2026-10-24 **Follow-up (owner's 6 items): done.**
  - **Ghana fixture:** budget raised to $140k/yr. The live web-UI run shortlisted MIT, Yale and Duke (Yale and Duke have verified employer lists), stopping at the 20-request cap during a Skeptic-requested revision.
  - **U.S. fixture:** re-run live with correct sponsorship statuses. The earlier buggy run is kept unedited and documented in `experiments/safety/malfunction_sponsorship_status.md`.
  - **Screenshots:** 8 new ones in `deliverables/screenshots/final/` (`ghana_0*`, `us_0*`).
  - **Tokenomics:** now covers all 4 clean runs.
  - **Run variability:** `docs/run_variability.md`.
  - **Secret scan:** `scripts/secret_scan.py` reports clean; `.env`, the raw DOL files, the copilot usage log and the accounts DB are git-ignored.
  - **Git:** repository initialized; first commit `8985bf2`; not pushed.
  - **UI fixes:** the evidence page no longer calls sponsorship "unknown" where employer filings exist, and no "Sign in" hint appears while accounts are off.
  - **Tests:** 266 passed, 1 skipped.
- 2026-10-24 **Follow-up 2 (owner's 6 items): done except Columbia and HBS, which need the owner's PDFs.**
  - **MIT Sloan employer list:** extracted from the official 2025-26 report by text colour (red = "hiring three or more MIT Sloan MBA students"), 27 employers, verified against the live PDF. The reviewed aliases were extended (Fidelity, IBM, Palantir…), giving 17 MIT employers with historical H-1B filings.
  - **HBS:** blocked (HTTP 202, empty page). Waiting for a manually saved PDF.
  - **Ranking:** Poets&Quants 2025-2026 U.S. MBA ranking (a composite of five rankings). All 30 programs verified in their table rows. Shown as context with the note "Rankings reflect prestige; AdmitCompass ranks by career fit."; never used in matching, default sort or prompts (tested).
  - **Ghana re-run:** hit 20/20 again (kept as evidence). The cap was raised to 25 and the re-run completed in 9 requests (MIT, Yale, Duke). The cost effect is in `clean_runs_analysis.md`.
  - **Guarantee rule:** the re-run exposed a false positive, fixed with negation now required in the same clause (`experiments/safety/false_positive_guarantee_negation.md`).
  - **Review zip:** removed.
  - **Tests:** 270 passed, 1 skipped; safety 26/26.
- 2026-10-24 **Columbia: official figures from files saved by the user (the pages return HTTP 403 to automated fetches).**
  - **Verified:** cost of attendance $143,030 and mandatory fees $6,783 (2026-2027, from a screenshot, each equal to an independently verified Poets&Quants value). Class of 2025: 90.4% accepted a job within 3 months and $175,000 median base (each found in a cell of the school's xlsx).
  - **Provenance:** each record has the URL, the retrieval date, "manually saved by user" and the file's SHA-256 (`data/sources/raw/supp/z_manual_columbia.json`). The saved files are git-ignored.
  - **Limit:** Columbia stays a discovery-tier (partial) program; "detailed" needs the official test-policy and STEM pages.
  - **Tests:** 271 passed, 1 skipped; secret scan clean.
- 2026-10-24 **Evidence + safety layer and run instrumentation.**
  - **Evidence:** each shortlisted program shows a per-claim table with status (verified / source-backed paraphrase / estimated / unknown), source, date checked, data period and tradeoff (`backend/app/tools/evidence_rows.py`).
  - **New guards:** admission-odds and personal-immigration questions are refused in code before any model call (`core/safety.sensitive_request`).
  - **Safety test mode:** `GET /api/safety/demo`, and "Safety test mode" in the dashboard reviewer footer. It runs five defenses on fixed unsafe inputs with no model call; 5/5 stopped.
  - **Run details:** `GET /api/demo/record` and `/api/runs/{id}/record`, plus the collapsed "Run details" panel with a JSON download. No keys and no profile fields; profile-derived tool arguments are masked.
  - **Tests:** 310 passed, 1 skipped; secret scan clean.
- 2026-10-24 **Ghana default sample, employer filing history, light-mode report screenshots.**
  - **Default sample:** the saved Ghana consulting run (`20261024T032006Z`) is now the default sample everywhere: `/api/demo`, `#/dashboard/demo`, the homepage and the International page. The India run stays at `#/dashboard/demo-india` (`?sample=india`).
  - **Employer filing history:** shown on shortlist cards (scoped to the target occupation and city) and on homepage program cards. Each line gives the top employers with FY2025 certified H-1B counts and links to the school list and the DOL data.
  - **Explore accuracy:** the badge now says "cost is a third-party estimate" when the shown cost isn't official (MIT Sloan).
  - **Weekly plan:** every week is listed and week 1 starts open; the unlock step is gone.
  - **Report screenshots:** saved to `deliverables/screenshots/report/` (light mode, 1440×900).
  - **Tests:** 314 passed, 1 skipped.
