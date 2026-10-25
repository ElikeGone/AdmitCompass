# Final submission audit — AdmitCompass (MGT 409)

Audited 2026-10-25 against the official requirements (live page re-read: https://zlisto.github.io/mgt_409_fa26/project_requirements.html; local copy `docs/rubric/official_requirements.md`). Commit audited: **`ca8414f`** (plus one uncommitted one-line fix, see §6). No paid model calls were made: every AI check ran in **mock mode** with the model key removed from the process environment. Nothing was pushed or committed.

## 1. Executive verdict: **NOT READY**, because of two owner actions

The application, setup, report and slides pass every executed check. Two **P0** items remain, and only the owner can resolve them:
1. **The GitHub repository isn't published.** Canvas requires the repo link.
2. **`report.html` shows "GitHub repository: Pending".** The report's first section requires the link.

One real bug that broke the README's own demo journey was found and fixed in the working copy ("Use a sample applicant" didn't advance the form, §6). **The fix is uncommitted and awaits approval.** After these three items are done, and the manual voice check in §9 is passed, the verdict becomes **READY WITH MANUAL CHECKS**.

## 2. Checklist

| # | Area | Check | Result |
|---|---|---|---|
| 1 | Setup | README has step-by-step Windows **and** macOS/Linux instructions | PASS |
| 2 | Setup | `.env.example` lists the right names, with no real values (`PORTKEY_API_KEY=` blank) | PASS |
| 3 | Setup | Only `PORTKEY_API_KEY` is needed for live AI (`OPENAI_API_KEY` listed as optional and unused) | PASS |
| 4 | Setup | `.env` **inside the repo** is loaded (shell key removed) | PASS |
| 5 | Setup | `.env` **one folder above** is loaded (shell key removed) | PASS |
| 6 | Setup | No key at all: the app runs; sample, Explore and safety work; Ask AI gives a clear 503; live run gives a clear 503 | PASS |
| 7 | Setup | Mock mode with no key: Ask AI answers, labeled "[Mock model — no AI call was made]", with citations | PASS |
| 8 | Setup | Dependencies install cleanly in a new venv | PASS |
| 9 | Setup | Clean `git clone` of committed HEAD → app answering in **67 s** (limit 600 s) | PASS |
| 10 | Setup | Clean clone from the **public GitHub URL** | **FAIL (P0): no remote exists** |
| 11 | Setup | No untracked local file is secretly required (the clone has only tracked files) | PASS |
| 12 | Setup | `.gitignore` covers `.env*`, `data/app/` (accounts DB), `logs/`, caches, venvs, raw DOL data and saved third-party pages | PASS |
| 13 | Security | Real key value absent from tracked files, git history, deliverables and local logs (matched by value, never printed) | PASS |
| 14 | Security | `scripts/secret_scan.py`: 276 files CLEAN | PASS |
| 15 | Security | Key-like strings in history are only placeholders or red-team fakes (`sk-redteam-secret-…`, `fresh-clone-placeholder…`, `your-course-key`) | PASS |
| 16 | Security | No personal emails, phone numbers or local user paths in tracked files; 0 of 126 tracked images carry metadata | PASS |
| 17 | Security | Screenshots that show accounts use only the fictional "Priya Test" | PASS |
| 18 | Routes | 29 backend routes discovered; 74 API assertions pass (§3) | PASS |
| 19 | Routes | Every frontend view loads by direct URL with no console errors; nav links work (§4) | PASS |
| 20 | Auth | Sign-up, validation errors, duplicate email, wrong password, sign-out, session restore, CSRF and origin checks, cross-user isolation | PASS |
| 21 | Ask AI | Typing, loading state, mock answer, citations, uncertainty, empty and oversized input, personal data, odds refusal, visa refusal, injection refusal, rate limit, cross-site block | PASS |
| 22 | Voice | Mic button and "Ready" state; permission denied → clear blocked message (browser automation) | PASS |
| 23 | Voice | Real microphone: grant, recognize, edit before sending, stop | **MANUAL CHECK (§9)** |
| 24 | Journeys | A–F (§4), including sponsorship shown as history and never a guarantee | PASS (D after fix) |
| 25 | Report | `deliverables/report.html`: offline, 7 numbered section headings present, **12 Letter pages**, "Page X of 12" on every page, 0 structural HTML errors | PASS |
| 26 | Report | GitHub URL present | **FAIL (P0): "Pending"** |
| 27 | Slides | `deliverables/slides.html`: reveal.js inlined, **10 slides**, offline, arrows, F/Esc full screen, no overflow at 1920×1080 or 1366×768, 0 network requests | PASS |
| 28 | Evidence | Safety, tokenomics and impact claims trace to their saved evidence (§7) | PASS |
| 29 | Tests | `pytest`: 323 passed, 1 skipped; Node voice tests: 19/19 | PASS |

## 3. Backend routes (API smoke test, mock mode, no key, fresh temporary DB)

**74 of 74 assertions passed** on the final run, against a server started from a clean clone of `ca8414f`. Two assertions failed on the first run. Both were my test's mistakes: the weekly plan is at `dashboard.workspace.weekly`, and my client mis-decoded UTF-8 on the Windows console. I corrected them and reran. The table lists the 70 distinct check labels.

| Route / check | Access | Expected | Result |
|---|---|---|---|
| `GET /health` | guest | 200 | PASS |
| `GET /` | guest | 200 | PASS |
| `GET /static/app.js` | guest | 200 | PASS |
| `GET /static/voice.js` | guest | 200 | PASS |
| `GET /api/config` | guest | 200 | PASS |
| `GET /api/fixtures` | guest | 200 | PASS |
| `GET /api/demo` | guest | 200 | PASS |
| `GET /api/demo?sample=india` | guest | 200 | PASS |
| `GET /api/demo/record` | guest | 200 | PASS |
| `GET /api/demo/record?sample=india` | guest | 200 | PASS |
| `GET /api/safety/demo` | guest | 200 | PASS |
| `GET /api/programs` | guest | 200 | PASS |
| `GET /api/programs/mit-sloan-mba` | guest | 200 | PASS |
| `GET /api/programs/not-a-program` | guest | 404 | PASS |
| `GET /api/dashboard/demo` | guest | 200 | PASS |
| `GET /api/dashboard/demo-india` | guest | 200 | PASS |
| `GET /api/dashboard/doesnotexist` | guest | 404 | PASS |
| `GET /api/runs/doesnotexist` | guest | 404 | PASS |
| `GET /api/runs/doesnotexist/record` | guest | 404 | PASS |
| `GET /api/copilot/status` | guest | 200 | PASS |
| `GET /docs` | guest | 200 | PASS |
| `GET /openapi.json` | guest | 200 | PASS |
| `GET /no-such-page` | guest | 404 | PASS |
| `safety demo content` | guest | 8/8 stopped | PASS |
| `dashboard: shortlist` | guest | MIT, Yale, Duke | PASS |
| `dashboard: weekly plan` | guest | weeks with actions | PASS |
| `programs list` | guest | 30 programs | PASS |
| `POST /api/runs (no confirm)` | guest | 400, no run | PASS |
| `POST /api/runs (confirmed, no key)` | guest | 503 before any model call | PASS |
| `POST /api/runs (injection in profile)` | guest | 422 field error, no echo | PASS |
| `GET /api/auth/me` | guest | user null | PASS |
| `signup: missing Origin` | guest | 403 (cross-site blocked) | PASS |
| `signup: valid` | guest | 201 + session cookie | PASS |
| `signup: duplicate email` | guest | 409 clear message | PASS |
| `session restore (me with cookie)` | auth | user returned | PASS |
| `save program without CSRF token` | auth | 403 | PASS |
| `save unknown program` | auth | 404 clear | PASS |
| `GET /api/account/saved` | auth | contains mit-sloan-mba | PASS |
| `PUT /api/account/profile (fixture)` | auth | 200 | PASS |
| `GET /api/account/profile` | auth | profile returned | PASS |
| `PUT profile with extra/PII field` | auth | 422 | PASS |
| `PUT /api/account/progress/demo` | auth | 200 | PASS |
| `GET /api/account/progress/demo` | auth | w1-0 done | PASS |
| `POST /api/account/import` | auth | 200, invalid skipped | PASS |
| `user B reads saved` | auth B | no A data | PASS |
| `user B reads progress` | auth B | no A data | PASS |
| `user B reads profile` | auth B | no A data | PASS |
| `POST /api/auth/logout` | auth | 200 | PASS |
| `me after logout` | guest | user null | PASS |
| `account after logout` | guest | 401 | PASS |
| `login wrong password` | guest | 401 generic | PASS |
| `login unknown email` | guest | 401 same message | PASS |
| `login correct` | guest | 200 + session | PASS |
| `saved data after re-login` | auth | persisted | PASS |
| `Ask AI: factual (mock)` | guest | sourced answer + citations, labeled mock | PASS |
| `Ask AI: empty` | guest | 422 clear | PASS |
| `Ask AI: >1000 chars` | guest | 422 | PASS |
| `Ask AI: personal data` | guest | 422 rejected | PASS |
| `Ask AI: admission odds` | guest | refused | PASS |
| `Ask AI: prompt injection` | guest | refused, no prompt leak | PASS |
| `Ask AI: personal visa question` | guest | refused (DSO/attorney) | PASS |
| `Ask AI: sponsorship (mock)` | guest | no guarantee; cited filings carry 'not a guarantee' | PASS |
| `Ask AI: unknown fact` | guest | unknown/estimate stated | PASS |
| `Ask AI: cross-site request` | guest | 403 | PASS |
| `Ask AI: rate limit (7 in a minute)` | guest | 429 after 6 | PASS |
| `POST /api/account/saved/mit-sloan-mba` | guest | 401 | PASS |
| `signup: bad email` | guest | 422 + field message | PASS |
| `signup: short password` | guest | 422 + field message | PASS |
| `signup: mismatched confirm` | guest | 422 + field message | PASS |
| `signup: empty name` | guest | 422 + field message | PASS |

**Routes discovered:**
- `GET /health`, `/api/config`, `/api/fixtures`, `/api/demo`, `/api/demo/record`, `/api/runs/{id}`, `/api/runs/{id}/record`, `/api/safety/demo`, `/api/programs`, `/api/programs/{id}`, `/api/dashboard/{id}`, `/api/copilot/status`, `/api/auth/me`, `/api/account/saved`, `/api/account/profile`, `/api/account/progress/{id}`
- `POST /api/runs`, `/api/copilot/chat`, `/api/auth/signup`, `/api/auth/login`, `/api/auth/logout`, `/api/account/saved/{id}`, `/api/account/import`
- `PUT /api/account/profile`, `/api/account/progress/{id}`
- `DELETE /api/account/saved/{id}`
- `/`, `/static/*`, `/docs`, `/redoc`, `/openapi.json`

**Not exercised:** the paid path of `POST /api/runs`, by design. Without a key it returns 503 before any model call.

## 4. Frontend pages and journeys (headless Chrome, mock mode, no key)

**47 of 47 checks passed** on the final run.
- **Fixed:** "Use a sample applicant" was failing until the fix in §6.
- **Script corrections:** I corrected my own selectors: the weekly plan uses "Mark done" buttons, Explore cards use "Details", and comparison is "Add to comparison" in the detail panel. The sign-up check now handles the import dialog, which appears correctly when a guest already has saved work.
- **Loading state:** observed separately with 1.5 s of added network latency: "Thinking… Checking the evidence…" shows, and the send button is disabled.

| Page / journey step | Access | Expected | Observed | Result |
|---|---|---|---|---|
| #/ (direct URL) | guest | renders (career|AdmitCompass) | h1="Your career ambition deserves a better e"; console errors 0; HTTP≥400 0 | PASS |
| #/start (direct URL) | guest | renders (starting from|work authorizati) | h1="Where are you starting from?"; console errors 0; HTTP≥400 0 | PASS |
| #/profile (direct URL) | guest | renders (starting from|work authorizati) | h1="Where are you starting from?"; console errors 0; HTTP≥400 0 | PASS |
| #/explore (direct URL) | guest | renders (Explore MBA programs) | h1="Explore MBA programs"; console errors 0; HTTP≥400 0 | PASS |
| #/how (direct URL) | guest | renders (How) | h1="From your career goal to a plan you can "; console errors 0; HTTP≥400 0 | PASS |
| #/intl (direct URL) | guest | renders (international) | h1="Plan an MBA when you'll need U.S. work a"; console errors 0; HTTP≥400 0 | PASS |
| #/dashboard/demo (direct URL) | guest | renders (Sample analysis) | h1="Sample analysis"; console errors 0; HTTP≥400 0 | PASS |
| #/dashboard/demo-india (direct URL) | guest | renders (Sample analysis) | h1="Sample analysis"; console errors 0; HTTP≥400 0 | PASS |
| #/results/demo (direct URL) | guest | renders | h1="Your shortlist"; console errors 0; HTTP≥400 0 | PASS |
| #/results/demo/plan (direct URL) | guest | renders | h1="Your roadmap"; console errors 0; HTTP≥400 0 | PASS |
| #/results/demo/evidence (direct URL) | guest | renders | h1="Evidence & risks"; console errors 0; HTTP≥400 0 | PASS |
| #/run/doesnotexist (direct URL) | guest | renders (Lost contact|not found|stopped) | h1="Your analysis is running"; console errors 0; HTTP≥400 0 | PASS |
| #/dashboard/doesnotexist (direct URL) | guest | renders (not found|couldn|unknown|isn't) | h1=""; console errors 0; HTTP≥400 0 | PASS |
| #/nonsense (direct URL) | guest | renders (career|AdmitCompass) | h1="Your career ambition deserves a better e"; console errors 0; HTTP≥400 0 | PASS |
| nav link "Explore Programs" | guest | #/explore | clicked=true, hash=#/explore | PASS |
| nav link "How It Works" | guest | #/how | clicked=true, hash=#/how | PASS |
| nav link "International Applicants" | guest | #/intl | clicked=true, hash=#/intl | PASS |
| nav link "Sample Analysis" | guest | #/dashboard/demo | clicked=true, hash=#/dashboard/demo | PASS |
| A. Sample Analysis → shortlist | guest | MIT Sloan, Yale SOM, Duke Fuqua shown; fictional label | all 3 programs present | PASS |
| A. Skeptic review visible | guest | Skeptic findings shown | Skeptic section present | PASS |
| A. sponsorship never invented | guest | 'not a guarantee' / unknown wording | 2 guarantee caveats | PASS |
| E. GRE/GMAT decision | guest | Undecided + diagnostics rationale | present | PASS |
| E. weekly plan | guest | This week's plan with Week 1 tasks | present | PASS |
| E. mark a weekly task done (guest, persists on reload) | guest | done state survives reload | clicked; after reload: Mark not done: Use up to 10 ho/pressed=true/checked=null | PASS |
| B. Explore search 'MIT' | guest | results narrow; MIT Sloan listed | cards before=5; MIT in results=true | PASS |
| B. Program detail (MIT Sloan) | guest | official $91,892 + labeled estimate | opened=true; official=true; estimate label=true | PASS |
| B. Add program to comparison | guest | comparison state updates | clicked=1; match=Compare 1 | PASS |
| C. International Applicants | guest | STEM/H-1B explained; no guarantee; unknowns | not-a-guarantee=true; DOL=true | PASS |
| D. Profile: load sample applicant | guest | fictional sample loaded, review step | clicked=true; fictional label=true | PASS |
| D. 'Run my analysis' button | guest | present | disabled | PASS |
| D. Start analysis with no key | guest | button blocked with reason | KEY_API_KEY on the server | PASS |
| D. Agent outputs + Skeptic on saved real run | guest | evidence/Skeptic rendered | len=2319; skeptic=true | PASS |
| F. Ask AI: empty input | guest | nothing sent | messages after empty send=0 | PASS |
| F. Ask AI: question → answer (mock) | guest | answer with citations; mock labeled | loading state seen=false; citations=12; mock label=true | PASS |
| F. Ask AI: uncertainty section | guest | 'What's uncertain' when unknowns exist | uncertainty element=true | PASS |
| F. Ask AI: admission odds | guest | refusal shown | doesn't estimate | PASS |
| F. Ask AI console errors | guest | none | 0 | PASS |
| Voice: mic button present (Chrome) | guest | button + Ready state | {"state":"ready","label":"Ready","aria":"Start voice input"} | PASS |
| Voice: permission denied (headless, CDP-denied) | guest | clear 'blocked' or 'unavailable' message | {"state":"unavailable","msg":"Microphone access is blocked. Allow it in your browser settings, or type your qu | PASS |
| Sign-up UI: empty submit | guest | field errors in plain language | Enter your name. / Enter a valid email address. / Enter your password. / Please fix the highlighted fields. | PASS |
| Sign-up UI: offer to import guest work | guest → auth | import dialog; import adds items | offered=true; Imported 0 saved programs and 1 completed task. | PASS |
| Sign-up UI: valid | guest → auth | signed in; header shows account | inputs=name,email,password,password_confirm; signout visible=true | PASS |
| Session restore after reload (UI) | auth | still signed in | signed in=true | PASS |
| Sign-out UI | auth → guest | Sign In shown again | signed out=true | PASS |
| Sign-in dialog opens from header after sign-out | guest | dialog with 2 inputs | header click=true; inputs=2 | PASS |
| Sign-in UI: wrong password | guest | generic error, no detail leak | Email or password is incorrect. | PASS |
| Sign-in UI: correct | guest → auth | signed in |  | PASS |

**Journey summary:**
- **A. Sample Analysis → recommendations:** MIT Sloan, Yale SOM and Duke Fuqua, with the fictional label, the Skeptic review and no-guarantee wording.
- **B. Explore → search → detail:** official $91,892 next to labeled estimates; adding to comparison works.
- **C. International Applicants:** DOL filings explained, never as a guarantee.
- **D. Profile → analysis:** the sample applicant loads; the paid-run confirmation appears; with no key, a clear 503 and no model call. The saved real run shows the agent outputs and the Skeptic.
- **E. GRE/GMAT → plan:** "Undecided" with a diagnostics rationale; week 1 tasks; marking a task done survives a reload.
- **F. Ask AI:** cited mock answer, uncertainty section, odds refusal.
- **Unknowns stay unknown:** MIT cost of attendance and international outcomes show as unknown or "not published"; there are no school-level sponsorship claims.

## 5. Commands run (exact), exit codes and results

| Command | Exit | Result |
|---|---|---|
| `python scripts/fresh_clone_test.py --keep --port 8766` (clone of `ca8414f`) | 0 | PASS: installed at 62 s, `/health` at **67 s**, `/` 200, `/api/programs` 200 |
| Clone server with `env -u PORTKEY_API_KEY -u OPENAI_API_KEY`, `.env` in parent / in repo / none / mock only | 0 | `api_key_configured`: true / true / false / false; mock Ask AI works |
| `python smoke.py <server>` (scratch API smoke) | 0 | 74/74 |
| `node journeys.mjs <server>` (scratch browser journeys) | 0 | 47/47 |
| `python -m pytest -q` | 0 | **323 passed, 1 skipped** (the skip is the optional live integration test) |
| `node --test tests/js/voice.test.mjs` | 0 | 19/19 |
| `node --check frontend/app.js` | 0 | syntax ok after the fix |
| `python scripts/secret_scan.py` | 0 | CLEAN (276 files) |
| `git log -p --all` pattern scan, plus a match on the real key value | — | 0 real-key matches; only fakes and placeholders |
| `python experiments/safety/run_safety_suite.py` | 0 | **26/26**; differs from the committed file only in timestamps and timings, so the committed evidence was restored |
| `python experiments/tokenomics/analyze_clean_runs.py` | **1** | crashes printing "→" to a Windows console (P2-3) |
| `PYTHONIOENCODING=utf-8 python experiments/tokenomics/analyze_clean_runs.py` | 0 | output **byte-identical** to the committed analysis |
| `python scripts/build_report.py`, `python scripts/build_slides.py` | 0 | rebuilds **identical** to the committed `report.html` and `slides.html` |
| Chrome `--print-to-pdf` of `report.html`, network blocked | 0 | 12 Letter pages; "AdmitCompass \| MGT 409" and "Page X of 12" on all 12 |
| `node testslides.mjs` (1920×1080 and 1366×768, network blocked) | 0 | 10 slides; arrows 1→10→1; F enters and Esc exits full screen; 0 overflow; 0 requests; 0 errors |
| Structural HTML check (Python `html.parser`: tag balance, duplicate ids) | 0 | report, slides, `index.html`: 0 errors, 0 duplicate ids. **Full W3C validation not run**: no offline validator is installed, and uploading the files was not appropriate |

## 6. Fix made (working copy, **uncommitted**)

**`frontend/app.js` → `loadFixture`**
- **Symptom:** on Find my pathway (`#/start`), clicking "Use a sample applicant" showed a "Loaded…" toast, but the form stayed on step 1 with no "Run my analysis" button. A reload didn't help, because the step counter lives in memory. The README tells graders to use exactly this flow.
- **Cause:** after loading the sample, the code set `location.hash = "#/start"`. The page was already on `#/start`, so no `hashchange` fired and nothing re-rendered. The button moved onto that page at some point, and this line wasn't updated.
- **Fix:** re-render in place when already on `#/start` or `#/profile`; otherwise navigate as before. One line plus a comment, mirroring the existing "Load my saved profile" button.
- **Verification:**
  - Before the fix, the reproduction stayed on step 1. After it, one click reaches the review step with "Run my analysis".
  - The journeys rerun passed 47/47, and the full test suite passed again.
  - The shared server on port 8001 serves this file from the working copy, so it already has the fix.

## 7. Evidence audit

- **Safety.**
  - **8/8:** reproduced live from `GET /api/safety/demo` in the clean clone. It runs production defense code on fixed inputs with no model call.
  - **26/26:** reproduced by `run_safety_suite.py`, using a scripted mock model.
  - **Labels:** the report and slides call both results **Mock-tested**, and say no paid model was attacked. Real budget stops (14/14 and twice 20/20) are labeled **Measured** and trace to `experiments/agent_runs/` and `clean_runs_analysis.md`.
- **Tokenomics.**
  - **Source:** every token number in the report and slides is generated from `clean_runs_analysis.json` and the saved run's `report.json` by the build scripts. `build_report.py` asserts that per-agent sums equal the run totals (9 requests; 54,756 input / 26,621 cached / 8,779 output).
  - **Projections:** ×4, ×400 and ×40,000 runs, labeled **Estimated**.
  - **Dollars:** "not calculated"; no price is invented anywhere.
  - **Optimization:** the cut (−29.4% requests, −29.9% estimated input tokens) matches `optimization_comparison.md`, is labeled **Mock replay** and is "not validated in a live A/B test".
  - **Regeneration:** the analysis regenerates byte-identical.
- **Impact.**
  - **Labels:** T1–T3 appear in both deliverables as **paraphrased recollections, not verbatim quotations**, with no quotation marks (checked automatically).
  - **No invented results:** no scores, completion rates, timings or time savings appear.
  - **Gap:** the report states it plainly: the rubric's "real user quote or before/after time" is **not met** (P1-4).

## 8. Outstanding issues

**P0: submission blockers**
1. **Publish the GitHub repository**, public or private with `zlisto` as a collaborator, then submit the link on Canvas.
2. **Put the URL in `report.html`:** edit `deliverables/report_src/report.template.html`, then run `python scripts/build_report.py` and commit.

**P1: important**
1. **Commit the sample-applicant fix (§6).** Without it, the README's demo journey looks broken to a grader.
2. **Rerun `scripts/fresh_clone_test.py --repo-url <GitHub URL>`** after pushing. Today's pass cloned the local repository.
3. **Fix `scripts/fresh_clone_test.py`'s environment.** It passes the parent shell's environment to the app. This shell has `PORTKEY_API_KEY` set, so the script's "api_key_configured=True" lines don't by themselves prove `.env` loading. That was proven separately here, with the key removed (checklist items 4–5). Suggested fix: start the child processes with `PORTKEY_API_KEY` and `OPENAI_API_KEY` removed. Two new PASS entries in `experiments/fresh_clone_test.md` are uncommitted.
4. **Impact evidence:** without a real-user quote or before/after time, that report section risks being capped at half points. Only a real tester session can fix this.
5. **Stop the shared server and tunnel when you're done.** A public Cloudflare quick tunnel (`cloudflared`) and a mock-mode server on port 8001 are still running from earlier in this session. Its account database (`shared_accounts.sqlite3`, in the session scratch folder, outside the repo) may contain accounts real testers created. Stop both and delete that file.
6. **No live-model verification in this audit.** Graders will use a real key. The last live evidence is from 2026-10-24: four-agent runs in `experiments/agent_runs/` and three live Ask AI questions in `experiments/copilot/live_check.md`. An optional, approved, low-cost live check of one Ask AI question before submitting would confirm the live path still works.

**P2: optional**
1. **Detail panel after browser Back:** the Explore detail panel stays open if you use the browser's Back button while it's open. In-app navigation is blocked by its backdrop.
2. **Invalid run link wording:** a nonexistent or expired run link (for example after a server restart) shows "Your analysis is running" for about 12 s, then "Lost contact with the server". The wording is misleading, but the case is rare.
3. **Tokenomics script encoding:** `analyze_clean_runs.py` crashes on a Windows console without UTF-8 output. Run it with `PYTHONIOENCODING=utf-8`.
4. **Stale numbers in `docs/evidence_index.md`:** rows 2 and 8 still say "266 passed" and "5/5 stopped" (now 323 and 8/8).
5. **README:** it doesn't point to `deliverables/report.html` or `slides.html`.
6. **Dependencies:** `requirements.txt` uses minimum versions, not exact pins.
7. **Report page numbers:** they print in Chrome and Edge only; Firefox and Safari ignore CSS margin boxes.
8. **Mock Ask AI wording:** for "Will McKinsey sponsor me?" the mock answer is repetitive ("historical h1b filings: documented" ×4). This is mock-only; the no-guarantee note is in every citation, and the live answer was fine.
9. **Untracked local files:** `scripts/fresh_clone_test.ps1` (the copy Defender flagged) and `deliverables/screenshots/auth-voice/`.
10. **Not done (optional):** the demo video and the ChatGPT side-by-side test.

## 9. Manual checks for the owner

**M1. Real voice input in Chrome (required to confirm checklist item 23)**
1. Start the app as in the README.
2. Open http://127.0.0.1:8000 **in Chrome** and click **Ask AI**. The mic button should say **Ready**.
3. Click the mic and choose **Allow** in Chrome's prompt. The state should change to **Listening**.
4. Say "What is Yale SOM tuition?" and check that:
   - the words appear in the question box;
   - nothing is sent automatically;
   - you can edit the text;
   - pressing **Enter** sends it and an answer arrives.
5. Click the mic again while listening: it should stop and return to **Ready**. Start listening again and close the Ask AI panel: listening should stop.
6. Go to Chrome's site settings → Microphone → **Block**, reload, and click the mic. It should show "Microphone access is blocked. Allow it in your browser settings, or type your question instead." Then set it back to Allow.
7. Optional: open the page in Firefox. It should show "Microphone unavailable", because Firefox has no speech recognition.

**Already covered by automation:**
- **Browser automation:** the mic button and "Ready" state, and the denied-permission message, were tested in headless Chrome.
- **Node unit tests:** unsupported browsers and the state machine are covered by the Node tests (19/19).
- **Earlier result:** you confirmed speech recognition with a physical microphone in Chrome on 2026-10-24.

**M2. After pushing:** run `python scripts/fresh_clone_test.py --repo-url <GitHub URL>` and confirm PASS.

**M3. Optional:** one live Ask AI question with the real key (a single small paid call), only if you approve it.

## 10. Cleanup

- **Clones:** both temporary clones are deleted.
- **Test data:** test accounts lived only in temporary databases, now deleted. Your `data/app/accounts.sqlite3` was never touched.
- **Servers:** the audit servers on ports 8766–8770 are stopped.
- **Left running:** your preview server on port 8000 and the shared server and tunnel (P1-5).
