# AdmitCompass — development changelog

Step-by-step development history, moved here from the README on 2026-10-24 (Task 4). Newest entries are at the bottom.

# AdmitCompass

**A career-first AI graduate education advisor for international applicants.**
MGT 409 — AI Foundations for Managers, Final Project.

## The problem
Prospective graduate students — especially international applicants — usually pick programs by ranking and brand, then discover too late that the program does not realistically lead to their intended career. The facts that matter most are scattered and easy to misread:

- Is the program actually STEM-designated (relevant to OPT/STEM OPT work authorization in the U.S.)?
- Do graduates land the target roles, and do the employers who hire them sponsor international hires?
- Is the GMAT/GRE worth taking, and which?
- What is the gap between my profile and the program, and what should I do this week?

Generic chatbots answer confidently without sources and often hallucinate STEM status or sponsorship. AdmitCompass makes evidence and uncertainty explicit.

## Intended users
- Primary: international applicants considering U.S. graduate business/STEM-adjacent programs (MBA, MS Business Analytics, MS Finance, MiM, etc.).
- Secondary: domestic career-switchers; admissions advisors who want a structured, sourced starting point.

## Differentiator — Career Pathway Intelligence Engine
Starts from the **career goal**, not the school. It links applicant profile → target careers → programs → verified program facts (requirements, STEM designation) → employment outcomes and sponsorship evidence → test guidance → gap analysis → weekly action plan. A **Skeptic agent** challenges weak recommendations before the user sees them. Every claim is labeled **Verified fact / Inference / Unknown / Advice**, with source URL and date for facts.

## MVP scope
1. Applicant profile intake (minimal data; no names, passport numbers, etc.)
2. Career-first program matching over a curated, sourced program dataset
3. Program fit + admissions requirements with evidence
4. STEM designation & work-authorization considerations (evidence-gated)
5. Employment outcomes & employer sponsorship evidence (evidence-gated)
6. GMAT/GRE decision guidance
7. Gap analysis + prioritized weekly action plan
8. Skeptic / Devil's Advocate review
9. End-to-end journey roadmap
10. Affordability check against the applicant's budget
11. Run trace: agent steps, sources, token usage and cost

## Out of scope (future phases)
Essay writing, visa application assistance, networking, recruiting, case prep, event planning. **Never in scope:** admission probabilities, guarantees of admission or sponsorship, admissions-committee simulation.

## Status
**Step 9B: colour, verification and link repair (pending review).** 22 of the 24 discovered programs were enriched with official-source facts and promoted to the evidence store (28 programs with sourced facts, 191 verified fields; 22 collector values downgraded after review; 7 enrichment facts re-checked by hand: 6 matched, 1 mismatch caught). Evidence status is computed per program: 5 detailed, 23 partially verified, 1 discovered, 1 retrieval unavailable. Every fact distinguishes *not published* from *not checked yet*. A polite link audit checked 193 URLs (`experiments/link_audit/`); all 100 fact-source URLs work. A controlled colour palette (blue, violet, cyan, emerald, amber) was added. 170 tests pass. Screenshots: `deliverables/screenshots/v5/`.

Rebuild data: `.venv\Scripts\python scripts\build_dataset.py` · re-check links: `.venv\Scripts\python scripts\link_audit.py`

**Step 10: AdmitCompass 4.0 visual reset — homepage + Explore.** Modern AI-startup identity: Plus Jakarta Sans + Inter (self-hosted, no serif fonts anywhere), white/#F5F7FB surfaces, #0F172A text, #2563EB primary, #14B8A6 accent. The homepage hero is an interactive product preview driven by the saved real analysis (career pathway → MBA options → target role; shortlist; next steps). Explore has a prominent search, filter controls, active-filter chips with reset, compact cards, save, compare (≤3) and details with source links. The other screens inherit the new fonts and colours but aren't redesigned yet. 155 tests pass. Screenshots: `deliverables/screenshots/v4/`.

**Step 9 (superseded): editorial homepage + Explore.** Editorial hero with an original SVG campus illustration and live counts, mobile menu, how-it-works, international-applicant section, and a sample preview. Explore now has career-keyword search (only industries/functions a school itself reports), evidence-level/state/cost/STEM filters, explained sorting, a View-details side panel (`GET /api/programs/{id}`), Save (browser-only) and Compare up to 3 with honest unknowns. Other screens are unchanged. 154 tests pass. Screenshots: `deliverables/screenshots/v3/`.

**Step 8: AdmitCompass 2.0 hybrid redesign + discovery foundation.** New design system (Instrument Serif + DM Sans, self-hosted). Redesigned landing, 5-step onboarding, **Explore programs** (6 programs with full evidence + 24 discovered from official university pages, labelled *Needs verification*; a periodically built index, not a live search), a calmer shortlist, a roadmap that leads with your next three moves, and a secondary *Evidence & risks* area. Discovered programs are never given to the agents. 151 tests pass. Screenshots: `deliverables/screenshots/v2/`.

**Step 7: safety, tokenomics and performance evidence.** 24/24 red-team scenarios pass (`experiments/safety/`). The optimized orchestrator uses 29% fewer requests in a controlled replay (`experiments/tokenomics/`). Local performance metrics are in `experiments/performance/`. The user-test protocol is ready, but no sessions have been run. Evidence map: `docs/evidence_index.md`. 124 tests pass.

**Step 6: interactive web app.** FastAPI serves a single-page app (plain HTML/CSS/JS, no build step) on top of the four-agent backend. You can view the saved real analysis at no cost, fill in a guided profile, start one live paid analysis (with confirmation and hard limits), and watch real agent events as they happen. 96 tests pass. Screenshots are in `deliverables/screenshots/`.

## Setup (tested on Windows, Python 3.14)
1. Clone the repo.
2. Put a `.env` containing `PORTKEY_API_KEY=...` in the repo folder **or one level above it**. The repo folder is checked first, and an already-set environment variable wins. See `.env.example`. *The saved demo works without a key; only live analysis needs one.*
3. Install:
   - Windows: `py -m venv .venv` then `.venv\Scripts\python -m pip install -r requirements.txt`
   - macOS/Linux: `python3 -m venv .venv` then `.venv/bin/python -m pip install -r requirements.txt`
4. Start the app: `.venv\Scripts\python -m uvicorn backend.app.main:app --port 8000` (macOS/Linux: `.venv/bin/python -m uvicorn backend.app.main:app --port 8000`)
5. Open **http://127.0.0.1:8000**
6. Optional: run tests with `.venv\Scripts\python -m pytest -q` (no paid calls; the one live test is skipped unless `ADMITCOMPASS_LIVE_TEST=1`).

## 2-minute demo walkthrough (v2)
1. **Landing** (`#/`): the career-first promise and one call to action.
2. **Explore programs** (`#/explore`): search, state, max verified cost, STEM-verified, sort by name / lowest verified cost / state; "Full evidence" vs "Needs verification" (open "Source" for the official page).
3. **Sample analysis** (`#/results/demo`): Shortlist → Roadmap → Evidence & risks. Each program shows why it fits, cost vs budget, STEM evidence and the biggest uncertainty; "Details & sources" expands the citations.
4. **Start** (`#/start`): 5 short questions plus a review. "Use a sample applicant" fills in a fictional profile. "Run my analysis" asks for confirmation before any paid call.

Discovery data: `data/discovery/` (see its README). Rebuild with `.venv\Scripts\python scripts\build_discovery_index.py`.

## 2-minute demo walkthrough (v1, superseded)
1. **Overview** explains the career-first approach and the four agents.
2. **Saved demo** (`#/results/demo`) opens the genuine gpt-6-luna analysis saved on 2026-10-23 for fictional applicant A. No AI call is made.
   - **Programs:** comparison table, program cards with labeled claims, and expandable official sources with verification level. Employment metrics are shown per program and marked not comparable.
   - **Strategy & plan:** GMAT/GRE guidance, prioritized gaps, a 10-week checklist, and a roadmap with "your decision" checkpoints.
   - **Skeptic & risks:** the Skeptic's finding, automatic safeguards, and unresolved unknowns.
   - **Agent trace & usage:** real token counts, runtime, cost "Unknown", and the 60-event chronological trace.
3. **New assessment** is a 4-step guided profile plus a review step. "Load demo applicant A/B" fills in fictional profiles. Applicant B has **no saved analysis**; only a live run can analyze it.
4. **Run live AI analysis** (optional, paid) asks for confirmation, then shows live agent progress, request/token/time meters, and an activity feed, and opens the results when finished. Limits: 20 requests, 200k tokens, 40 tool calls, 300 s, 1 revision, 1 run at a time, 3 runs per server session.

## Reproduce the Step 7 evidence (no paid calls)
- Safety matrix: `.venv\Scripts\python experiments\safety\run_safety_suite.py`
- Real-run tokenomics: `.venv\Scripts\python experiments\tokenomics\analyze_runs.py`
- Baseline vs optimized: `.venv\Scripts\python -m pip install -r experiments\requirements-experiments.txt`, then `.venv\Scripts\python experiments\tokenomics\optimization_experiment.py`
- Performance: `.venv\Scripts\python experiments\performance\measure.py`

## Live-run safety
- Paid runs require an explicit `confirm_paid_run=true`. Only one can run at a time, with at most 3 per server process (`ADMITCOMPASS_MAX_LIVE_RUNS_PER_SERVER`).
- Requests can't set the model, prompts, budgets, or evidence data (unknown fields → HTTP 422).
- Run ids are generated by the server. Profiles stay in memory only. API keys are redacted from any error text.
- The frontend inserts all text with `textContent`, never raw HTML. The trace has metadata only: no prompts, no model reasoning.

## Repo layout
```
backend/   Python FastAPI service: agents/, tools/, schemas/
frontend/  Interactive UI
data/      sources/ (evidence snapshots), programs/ (curated program dataset), fixtures/ (test profiles)
tests/     Unit + golden-case tests
experiments/  Prompt/model evaluations, cost measurements
deliverables/ Final report, slides, demo materials
docs/      Spec, build plan, decisions, rubric tracker
```

## Docs
- [Product spec](docs/product_spec.md) · [Build plan](docs/build_plan.md) · [Decisions](docs/decisions.md) · [Rubric tracker](docs/rubric_tracker.md) · [AI prompt log](AI_prompts.md)

## Disclaimer
AdmitCompass provides decision support, not admissions, legal, or immigration advice. Consequential decisions (applying, paying deposits, visa/work-authorization planning) require the applicant's own judgment and verification with schools and qualified advisors.

**Step 10: Career Intelligence dashboard (pending review).**
- **Route:** `#/dashboard/demo`. "Sample analysis" now opens it, and the old `#/results/...` pages still work.
- **Five sections:**
  1. Career pathway: strengths from your profile vs AI-inferred gaps.
  2. Program fit, with an interactive shortlist.
  3. Affordability: a budget-minus-COA gap, only when both are per academic year.
  4. International feasibility: STEM, outcomes and sponsorship, plus a "STEM ≠ sponsorship" note.
  5. Application workspace: 40 tasks grouped by roadmap phase; mark complete, undo and reset, saved in this browser; officially sourced deadlines only.
- **How it's computed:** deterministic code in `backend/app/tools/dashboard.py`, served by `GET /api/dashboard/{run_id}`. No model calls.
- **Results:** 181 tests pass. Validation is in `experiments/dashboard/validation_report.md`; screenshots are in `deliverables/screenshots/v7/`.

**Homepage polish and sign-in entry points (pending review).**
- **Header:** a new top header with Explore Programs, How It Works, International Applicants and Sample Analysis, plus Sign In / Sign Up buttons.
- **Hero:** a two-column hero with a larger interactive preview (5 tabs: pathway, programs, affordability, international, next steps), built from the saved run through `/api/dashboard/demo`. Its counts come from the live evidence store.
- **Sections:** a four-step How It Works section, a six-program showcase with each card's evidence status, a redesigned international section, a closing call to action and a new footer.
- **Accounts:** AdmitCompass has no authentication backend. Sign In and Sign Up open an honest "Coming soon" dialog with "Continue without account". There are no password fields and nothing is stored.
- **Results:** 182 tests pass. Screenshots are in `deliverables/screenshots/v8/`.

**Step 11: user accounts (pending review).**
- **What works:** email and password sign-up, sign-in and sign-out, with sessions kept on the server in SQLite. Saved programs, profile and roadmap progress are linked to the account, and there is an opt-in import of browser-local data.
- **Security:** passwords are hashed with scrypt; the session cookie is HttpOnly and SameSite=Lax; CSRF is checked by Origin plus a token; failed sign-ins are rate-limited.
- **Setup and limitations:** see `docs/accounts.md`. There is no password reset (no email service), and it is not production-ready without a security review.
- **Results:** 198 tests pass. Screenshots are in `deliverables/screenshots/v9/`.

**Step 12: Ask AdmitCompass AI copilot (pending review).**
- **What it is:** a chat panel on every page. Each question gets deterministic evidence retrieval and **one** bounded gpt-6-luna call, never the four-agent pipeline. Answers carry numbered citations to official pages and explicit uncertainties. Grounding with one repair falls back to sourced facts if needed. The panel offers context-aware suggestions and follow-ups, and the context it sends is visible and removable.
- **Safety:** checks for prompt injection and personal data, plus rate, input and output limits.
- **How it was tested:** all tests mock the model, and browser testing used `AC_COPILOT_MODE=mock`. **No live copilot call has been made yet.**
- **More:** see `docs/copilot.md`. 220 tests pass. Screenshots are in `deliverables/screenshots/v10/`.

**Step 14: MBA research engine (pending review).**
- **What was added:** a supplementary evidence layer with 176 independently validated facts across 29 programs (44 official, 78 reported by third parties, 54 third-party estimates).
- **What the UI shows:** official tuition, official cost of attendance, Poets&Quants estimates and Clear Admit compiled costs as separate, labeled lines; official class profiles, scholarships and 2026–27 deadlines for 10 programs; precise gap reasons instead of "Not published"; no coverage ratios.
- **Copilot:** it cites these facts and can't call an estimate official.
- **Rebuild:** `.venv\Scripts\python scripts\make_secondary_raw.py`, then `.venv\Scripts\python scripts\build_supplementary.py` (add `--offline` to reuse the cached pages).
- **Results:** report in `experiments/research/research_report.md`; 236 tests pass.
