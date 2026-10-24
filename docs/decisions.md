# Architecture Decision Log

## ADR-001 — Technology stack (Revised 2026-10-23, Step 2)
**Decision:** Python 3.11+, FastAPI + Pydantic, **OpenAI Python SDK pointed at Portkey** (`https://api.portkey.ai/v1`) using model **`gpt-6-luna`** with the course `PORTKEY_API_KEY`; frontend = static HTML + vanilla JS (+ Tailwind/Alpine via CDN) served by FastAPI; pytest; JSON evidence store.
**Why:** Course rules allow only `gpt-6-luna` on the course key. The OpenAI-compatible-via-Portkey pattern already worked in hw3 (`hw3/agent.py`). No Node build → fast fresh-clone setup.
**Superseded:** Step 1 plan to use the Anthropic SDK/API in the app. Claude Code is only the development assistant. No Anthropic API in the app unless the user explicitly approves a paid personal key.

## ADR-002 — Code orchestrator, sequential pipeline with one Skeptic revision loop (Kept)
Plain Python orchestrator. Easier to trace, test, cap cost, and explain in the report than an autonomous framework.

## ADR-003 — Curated evidence store, not live web search (Kept)
Hand-verified program facts with URL + retrieved date in `data/`. Small dataset doubles as the required "small test dataset". Reproducible; prevents hallucinated STEM/sponsorship.

## ADR-004 — Single model, cost controlled by design (Revised)
Only `gpt-6-luna` is permitted, so model tiering is replaced by: deterministic tools for anything computable, compact JSON evidence passed instead of raw text, stable system-prompt prefixes to maximize cached tokens, output length caps, and a per-run cost ceiling. Prices for `gpt-6-luna` must be confirmed from course/Portkey info before tokenomics (unknown now).

## ADR-005 — Privacy by minimization (Kept)
No PII fields; session-only state; traces store anonymized fixtures only.

## ADR-006 — Environment loading (New)
`load_dotenv(REPO/.env)` then `load_dotenv(REPO.parent/.env)` (repo values win; no override). Fail fast with a clear message if `PORTKEY_API_KEY` is missing. Verified by a fresh-clone test with `.env` placed only one level above the clone.

## ADR-007 — Lean agent design: 7 → 4 agents (New)
Review of Step 1's 7 agents: several were thin wrappers (Profile Analyst, Test Strategy) or did lookups better done deterministically (Program Verifier). Each kept agent must make a judgment no code can, use distinct tools, and produce a typed output another agent consumes.

| Agent | Unique contribution | Tools (deterministic Python) | Output → handoff |
|---|---|---|---|
| **1. Pathway Matcher** | Translates goals + profile into target roles and ranks programs by career fit (not prestige); flags missing profile info | `search_programs(filters)`, `get_program_summary(id)` | `PathwayPlan` (roles, shortlist w/ rationale) → Evidence Analyst |
| **2. Evidence Analyst** | Interprets evidence for each shortlisted program: requirements, STEM status, outcomes, sponsorship strength, affordability vs budget; labels every claim | `get_evidence(program_id, topic)`, `compute_cost_of_attendance(...)`, `check_source_freshness(...)` | `ProgramDossier[]` with labeled, sourced claims → Planner, Skeptic |
| **3. Strategy Planner** | GMAT/GRE/waiver decision, gap analysis, prioritized weekly schedule, journey roadmap with human checkpoints | `deadline_calendar(programs, today)`, `get_requirements(id)` | `ActionPlan` → Skeptic |
| **4. Skeptic** | Adversarially challenges recommendations: unsupported facts, stale sources, budget/visa mismatches, overconfidence | `audit_claims(output)` (rule-based validator), `get_evidence(...)` | `Critique[]` (severity, target claim, required fix) → orchestrator triggers ≤1 revision of agent 1/2/3 |

**Orchestrator (code, not an agent):** validates schemas, enforces evidence gates (no `verified_fact` without URL+date; STEM/sponsorship default `unknown`), sanitizes inputs, tracks tokens/cost, stops at the per-run cap, records the trace shown in the UI.
**Tradeoff:** fewer agents = less "agent count" theater but clearer, testable handoffs and lower cost — better for the agent-design and tokenomics rows.

## ADR-008 — Step 3 foundation choices (New, 2026-10-23)
- **Portkey config** copied from the course setup that already worked (`hw3/agent.py`): OpenAI SDK, `base_url=https://api.portkey.ai/v1`, headers `x-portkey-api-key` + `x-portkey-provider: openai`. Verified by a real call on 2026-10-23; Portkey returned model `gpt-6-luna-2026-09-22`.
- **Model lock:** `config.get_settings()` rejects any `ADMITCOMPASS_MODEL` other than `gpt-6-luna`. No fallback model.
- **Structured output:** JSON mode (`response_format=json_object`) + JSON Schema in the system prompt + Pydantic `model_validate_json`. This is portable across Portkey and makes validation failures explicit. Strict `json_schema` mode can be tested later as a cost/quality option.
- **No smoke-test HTTP endpoint:** the smoke test is a CLI script (`scripts/smoke_test.py`) so a public URL can't spend the key. `/health` reports only status, model name, and whether a key exists (boolean).
- **Cost = unknown** until a documented `gpt-6-luna` price is added to `PRICES_PER_MTOK` in `backend/app/core/usage.py`. Note: the API returns the dated snapshot name, so price lookup must map snapshot → `gpt-6-luna` (Step 4).
- **Python 3.14 venv** (only interpreter installed). Python 3.11+ is expected to work but hasn't been tested.

## ADR-009 — Program dataset and evidence layer (New, 2026-10-23, Step 4)
- **Collection:** six research subagents (one per school) fetched official university pages and recorded URL, title, and excerpt for each field. Raw notes are kept in `data/sources/raw/`. `scripts/build_dataset.py` converts them deterministically. The main session re-fetched 5 facts as a spot check, and all matched.
- **Strict downgrade rule:** values the collector flagged as unreliable are stored as `unknown`, with the candidate value kept in the note. These are Duke's industry/function and Rice's industry/international breakdowns (misaligned PDF table text), and MIT's function breakdown (its narrative contradicts its own table). Reason: a wrong "verified" number is worse than an honest unknown.
- **Partial breakdowns** (Booth's top-6 industries and top-5 functions; MIT's partial industry list) stay verified, and their definition says they are partial.
- **Sponsorship** is its own fact type: it must name an employer and quote a statement. No such evidence was found, so all 6 programs are unknown. Employer lists never count.
- **Rice employment PDF** is hosted on the career office's vendor CDN (`cdn.uconnectlabs.com`), linked from `cdo.business.rice.edu/reports`. It is labeled official, with a note.
- **Paraphrase flag:** 13 excerpts are fetch-tool paraphrases, not verbatim quotes. The UI must show this flag.
- **`Claim.evidence_ids`** was added so agents cite store evidence by id. `EvidenceStore.validate_claim` rejects unknown ids and sources that weren't accessed.

## ADR-010 — Agents, orchestrator, and Responses API (Step 5, 2026-10-23)
- **Four agents, each with its own tools:** Pathway Matcher (`search_programs`, `get_program_overview`); Evidence Analyst (`get_program_facts`, `get_evidence`, `compare_employment_metrics`); Strategy Planner (`get_program_facts`); Skeptic (`get_evidence`, `get_program_facts`, `compare_employment_metrics`). The tools are read-only and deterministic, and every call is logged with the agent that made it.
- **Orchestrator in code:** fixed sequence, then at most 1 Skeptic-requested revision (the target agent plus the agents after it; the Skeptic is not re-run). Up to 4 tool rounds per agent, 1 retry for invalid JSON, 1 retry for grounding errors, then fail closed.
- **Grounding in code** (`backend/app/agents/grounding.py`): program and evidence ids must exist and evidence must belong to the program; numbers in verified claims must appear in the cited evidence or the applicant profile; STEM, sponsorship, and affordability are overwritten with values computed from the store; metric comparability is decided by a fixed rule (same cohort and definition); admission odds, guarantees, visa-eligibility assertions, and invented calendar dates are flagged or dropped. Program facts in the report come from the store, never from model text.
- **API change:** `/v1/chat/completions` rejected function tools with reasoning on gpt-6-luna (HTTP 400). A minimal `/v1/responses` tool test succeeded first (`experiments/smoke_test/responses_tools_*.json`), so agents now use the Responses API: stateless (`store=False`), encrypted reasoning items passed back between turns, JSON output mode, reasoning effort `low` (configurable with `ADMITCOMPASS_REASONING_EFFORT`). Same model, `gpt-6-luna`.
- **Budget:** defaults raised from 14 requests / 120k tokens to 20 / 200k after the measured run (14 requests used only by the time the Strategy Planner started). Tool calls stay capped at 40.
- **Fixes found by the real run:** the number check now allows applicant-profile numbers (it previously dropped correct budget comparisons); identical repeat tool calls are cached.

## ADR-011 — Observations from the first complete run (2026-10-23)
- **Portkey response caching:** identical requests appear to be replayed from a cache (identical usage, ~0.2 s). Tokenomics experiments must state whether a run could hit the cache and vary inputs for fresh measurements. Whether replays are billed is unknown.
- **Trace completeness:** grounding events now log violation details on the first pass too.
- **Post-run audit:** `scripts/verify_run.py` re-checks a saved report with no model calls (evidence ids, numbers in all free-text fields, comparability, STEM/sponsorship). This covers free-text fields (fit rationale, tradeoffs) that the in-run grounding does not check numerically.
- **Not changed yet (candidates for the cost experiment):** cheaper grounding retries, downgrading evidence-less verified claims instead of retrying, overviews inside `search_programs`, passing dossier facts to the Planner.

## ADR-012 — Web app architecture (Step 6, 2026-10-23)
- **Kept FastAPI + plain HTML/CSS/JS** (no framework, no build step, no new dependencies) so a fresh clone runs in minutes. Hash routing; deep-linkable result tabs.
- **Background thread + polling** (`backend/app/runs.py`): one live run at a time (HTTP 409), capped live runs per server process (HTTP 429, default 3), server-generated run ids. The UI polls `GET /api/runs/{id}?since=n` every 1.2 s and renders the orchestrator's real trace. Chosen over websockets/SSE for simplicity and reliability in a single-user local demo.
- **Wall-clock limit** added to `RunBudget` (`ADMITCOMPASS_MAX_SECONDS_PER_RUN`, default 300 s). It is checked before every model request.
- **Secret redaction moved into the orchestrator** (`redact_secrets`) after an API test showed that an upstream error containing the key would have reached the trace and the report.
- **Saved demo** is served from the real run folder (`experiments/agent_runs/20261023T180104Z…`), with its verification audit. The second fictional applicant can only be analyzed live; no output was invented for it.
- **Honest UI labels:** model free text prefixed "verified_fact" is shown as "From sources", not "Verified fact"; data-period-unknown freshness notes are hidden as noise; the Portkey cache caveat and the known false-positive flag are shown on the saved demo.

## ADR-013 — Safety hardening, budget periods, and cost optimization (Step 7, 2026-10-23)
- **Deterministic input screens** (`backend/app/core/safety.py`): instruction-like text and personal identifiers (email, phone, passport/ID, SSN, DOB) are rejected in every profile string. Instruction-like text in evidence excerpts or source titles makes the dataset fail validation. Tool results reach the model as `{"note": untrusted-data notice, "data": ...}`.
- **New grounding rules:** sponsorship/visa and STEM claims labelled verified must cite evidence of that fact type, unless the sentence is hedged ("... is unknown"); scholarship-odds language is flagged; a hedge *after* a risky word (e.g. "... guaranteed ... is unsupported") no longer causes a false positive. Trade-off: a real guarantee followed by a hedge in the same clause could be missed by the flag. Verified claims still need evidence.
- **Budget period is explicit** (`budget_usd` + `budget_period`). Whole-program budgets are never divided; affordability is "unknown" with a deterministic explanation, because schools publish cost per academic year. Legacy `max_total_budget_usd_per_year` still means per year.
- **Cost optimization (default on):** repair-mode grounding retry (1 request, no tools, previous answer + errors + already-retrieved evidence) and relabelling evidence-less `verified_fact` claims as `inference` instead of a schema retry. In a controlled replay: 17 → 12 requests, −29.9% estimated input tokens, quality identical apart from that relabelling. `Orchestrator(optimized=False)` keeps the old behaviour for comparison.
- **Correction:** the cache-replay range is requests 1–9 (not 1–13 as first written in ADR-011 / RUN_LOG). Fixed in RUN_LOG and the UI.
- **Price:** no documented gpt-6-luna price found (course site, instructions, requirements, provider config). Cost stays unknown; only clearly labelled hypothetical scenarios are given.
- **UI provenance labels:** "Official university source", "Re-fetched and matched by a second check" vs "Captured by a research agent; not independently re-checked", "Paraphrase" vs "Excerpt as captured".

## ADR-014 — Hybrid redesign and a separate discovery tier (Step 8, 2026-10-23)
- **Why redesign:** user feedback said the v1 UI was overcrowded, the typography unpleasing, and six schools too constraining. The audit is in `docs/redesign_plan.md`.
- **Design system:** ivory #F8F7F3, navy #18283D, muted teal #397F79, sage #E7EBE7; Instrument Serif for display headings only; DM Sans for everything else. Fonts are self-hosted (`frontend/fonts/`, SIL OFL) so the app needs no CDN; Georgia / system-sans fallbacks. At most two tags per card; detail behind disclosures.
- **Discovery tier, not verified data:** `DiscoveredProgram` forbids extra fields (so no tuition/STEM/outcome/sponsorship), status ∈ {needs_verification, not_confirmed} and never verified, https provenance, injection-screened text, fetched ⇒ excerpt. Discovered records are kept out of `EvidenceStore` and the agent tools (tested).
- **Source choice:** official university program pages, fetched one by one (24 seeds chosen by the author; 21 fetched, 3 blocked: 403×2, TLS×1). The AACSB directory was evaluated as a future seed list but not used for facts (no export seen, terms not reviewed). Labelled in the UI as a periodically built index, not a live search.
- **Merge rule:** the verified record wins on a normalized university-name match or a shared `.edu` registrable domain; duplicates inside discovery collapse; all counted.
- **Promotion (not implemented):** a discovered program becomes recommendable only by going through the per-fact evidence pipeline (`scripts/build_dataset.py`): official sources per fact, dates, excerpts, audit. Never by flipping a status.
- **Engineering lesson:** native `Node.append()` stringifies arrays and `null` ("[object HTMLElement]", "null"). This bit us twice, so all appends now go through `put()`, which has el()'s semantics, and a test forbids `.append(` in `app.js`.

## ADR-015 — Homepage and Explore v3 from a visual reference (Step 9, 2026-10-23)
- **Reference used for the look, not the content:** invented numbers ("100+", "124 programs found"), campus photos, the "Sign in" link, and per-program career narratives in the reference were not copied. The stats card shows live API counts (6 verified, 24 discovered) and the fixed number of agents (4).
- **Imagery:** an original SVG illustration (`frontend/img/campus.svg`) instead of photos: no licensing issues, small, crisp at any size, and it doesn't imply a specific school.
- **Career-keyword search is grounded:** keywords come only from the `industry_breakdown` / `function_breakdown` facts a school publishes (currently MIT Sloan and Chicago Booth). Cards explain the match ("an industry or function this school reports hiring into"). No inferred program-career mapping.
- **Details and compare:** new read-only `GET /api/programs/{id}` (verified: all 13 facts + evidence; discovered: record only). Compare is capped at 3; discovered programs show "Not verified" for every fact; employment is shown with its definition and never ranked. Save uses `localStorage` only (no accounts, no server storage).
- **Mobile:** menu button below 1080 px (`aria-expanded`, Esc to close, closes on navigation); hero reflows to copy → illustration → stats card.
- **Styles** live in a separate `frontend/styles-v3.css` so the not-yet-redesigned screens are untouched.

## ADR-016 — AdmitCompass 4.0: modern AI-startup identity (Step 10, 2026-10-23)
- **Why:** the user rejected the editorial/academic look (thin serif, cream background, campus illustration). Direction A, "Modern AI Startup", was chosen.
- **Tokens:** Plus Jakarta Sans (headings, `--display`) and Inter (UI), both self-hosted under the SIL OFL; #FFFFFF / #F5F7FB / #0F172A / #475569 / #2563EB / #14B8A6; radius 12–16 px; restrained shadows. Instrument Serif, DM Sans and the campus SVG were deleted. A test forbids serif typefaces in the CSS and checks that the font files are bundled.
- **Global tokens, local redesign:** the legacy token names in `styles.css` now carry the new palette and fonts, so unredesigned screens (onboarding, results, run) lose the serif/cream look without being restructured. Their layouts are unchanged pending approval.
- **Product-led hero:** an interactive preview built from `/api/demo` (the saved real run): background → MBA options (click to switch) → target role, with each program's real cost, budget fit, STEM status and biggest uncertainty. The shortlist bars show cost as a share of the applicant's budget, explicitly not a score. No fabricated fit scores, outcomes or imagery.
- **Explore:** same `/api/programs` contract and 30-program index. New UI: search, select filters, STEM/Saved toggles, active-filter chips with per-chip removal and "Reset all", cards with a three-fact strip (cost / STEM / employment*) that shows "Unknown" when unsupported, a status line separating full evidence from needs-verification and not-retrieved, a compare tray (≤3), and details/compare drawers with official source links.
- **Breakpoints:** 1100 (3→2 card columns), 980 (menu button), 960 (hero stacks), 768 (1 column), 560 (phone).

## ADR-017 — Enrichment, safe promotion, evidence status and link audit (Step 9B, 2026-10-23)
- **Collection:** 4 research subagents gathered per-field official-page evidence for the 24 discovered programs (`data/sources/raw/enrich/`), using the same raw format as Step 4 plus `unknown_reasons` (checked vs not checked) and a new `application_deadlines` field.
- **Review before promotion (main session):** 22 collector values were downgraded to unknown with the reason kept. Examples: resident-only tuition/costs (UT, UNC, Haas), STEM silence recorded as "not designated" (Texas A&M, Minnesota), multi-year multi-program outcomes (Minnesota), medians not stated as base (Wharton, NYU), program fees recorded as tuition (UCLA), ambiguous expense labels (Kellogg), and Cornell STEM after a spot check showed only the *curriculum* is described as STEM. 7 enrichment facts were re-fetched by hand (Stanford ×2, Tuck ×2, CMU ×2 match; Cornell STEM mismatch → downgraded).
- **Fill-only merge:** curated (Step 4) records always win; enrichment may only fill fields they left unknown (`merge_raw`, tested).
- **Safe promotion:** an enriched program joins the evidence store (and becomes visible to the agents) only with ≥ 2 verified facts beyond location and only through the same Pydantic validation. Columbia (403) and Kelley (collector TLS failure) stay in the discovery tier.
- **Checked vs not checked:** `Fact.checked`. A collector reason saying a page was "not fetched" counts as *not checked*, regardless of the collector's label (Wharton STEM was mislabeled; regression test).
- **Evidence status (computed, not asserted):** *Detailed* = cost, STEM (whole degree), tests and outcomes all sourced and ≥ 8 facts; *Partially verified* = otherwise in the evidence store; *Discovered* = existence confirmed only; *Retrieval unavailable* = the official page couldn't be retrieved. STEM covering only some tracks shows as "Some tracks" and doesn't count toward Detailed. A page loading never upgrades a program.
- **Link audit:** `scripts/link_audit.py` (honest UA, 4 concurrent, 20 s timeout, 1 retry, no bypass) → `experiments/link_audit/link_audit.csv` + `data/links/link_status.json`, which the UI uses to label links (redirects show their final URL; blocked links are shown with an explanation, not hidden).
- **Colour:** `frontend/styles-color.css` — blue actions, violet AI insights, cyan discovery, emerald verified, amber needs-checking; tints only.
- **Agents:** they now see 28 programs. The saved demo is unchanged (it is a saved run); the safety suite still passes 24/24.

## ADR-018 — Dark theme by default (2026-10-23)
- **Why:** the user preferred a darker background to plain white.
- **How:** `frontend/styles-dark.css`, loaded last, remaps the existing tokens (page #0A0F1E, surfaces #111A2E/#16213A, text #E6EBF5/#A8B3C7) and re-surfaces components that hard-coded white. Accents are slightly brightened (blue #3B82F6, violet #8B5CF6, cyan #22D3EE, emerald #34D399, amber #FBBF24); primary buttons stay #2563EB so white text keeps ≥ 4.5:1 contrast.
- **Checked:** an automated scan of 7 screens found no light surfaces and no text below 4.5:1 contrast after fixes; no horizontal overflow at 1440 and 375 px. Layouts are unchanged.

- Theme toggle (2026-10-23): header button switches light/dark by enabling/disabling `styles-dark.css`; choice saved in localStorage key `ac-theme`; a pre-paint script in `<head>` applies it to avoid a flash; dark is the default; `aria-pressed` reflects dark mode.

## ADR-019 — Career Intelligence dashboard (Step 10, 2026-10-23)
- **Read-only, deterministic.** `GET /api/dashboard/{run_id}` combines the saved or live report with the current evidence store and makes no model calls.
- **Budget gap.** Computed only when the budget is per academic year and the cost of attendance is verified for an academic year. Tuition is never compared with a total budget. Otherwise the dashboard says "Not enough comparable data".
- **Labels.** Profile facts and AI-inferred gaps are labeled separately. Fit shows only evidence-linked claims as "supported".
- **Sponsorship.** Shown as unknown unless there is employer-specific evidence.
- **Deadlines.** Shown only when verified with a cycle.
- **Progress storage.** `localStorage` key `ac-workspace-<report run_id>`, holding task ids and done flags only. Undo is in-session; reset asks for confirmation.
- **Known issue.** The saved MIT rationale compares tuition with the budget. The text is kept verbatim (labeled AI inference) and disclosed in the validation report.

## ADR-020 — Homepage polish and authentication entry points (2026-10-23)
- **No auth backend exists**, and none was added in this milestone. `#/signin` and `#/signup` open an accessible dialog (focus trap, Escape, focus returned to the opener) labeled "Coming soon". It has no inputs and stores nothing. "Continue without account" goes to `#/start`. Closing the dialog restores the previous URL without re-rendering the page.
- **No invented facts.** The hero preview uses only `/api/dashboard/demo`. The concept image's MIT cost figure, "Top choice" label and stats were not copied. MIT shows "Not published" for cost of attendance.
- **Showcase.** It shows the first 6 programs from the evidence store with their computed evidence status. The footer line states the discovered-only and unavailable counts.
- **Themes.** The hero is always dark; the other sections follow the light/dark theme, which stays dark by default.
- **International outcomes.** A sourced statement counts as an outcome figure only if it states a % or $ statistic. This fixed Booth being labeled "Official" in both the dashboard and the preview.

## ADR-021 — Real user accounts (Step 11, 2026-10-23)
- **Replaces the "Coming soon" dialogs.** Accounts use SQLite through a small parameterized data-access layer (`backend/app/auth/store.py`). There are no new dependencies.
- **scrypt rather than Argon2id.** Argon2id would need `argon2-cffi`, which isn't installed. scrypt from the standard library is memory-hard and accepted by OWASP. The stored format includes its parameters, so they can be upgraded later.
- **Server-side sessions.** Only the token's SHA-256 is stored. The HttpOnly cookie expires after 7 days absolute or 24 hours idle, and the session rotates on sign-in.
- **CSRF.** An Origin check applies to all auth and account writes, plus a per-session token header on signed-in writes. No CORS.
- **Guest data stays in the browser.** Import is opt-in and additive only.
- **Full details:** `docs/accounts.md` covers deployment requirements and limitations: HTTPS, SQLite persistence, no password reset or email verification.

## ADR-022 — Ask AdmitCompass copilot (Step 12, 2026-10-23)
- **One bounded call per question.** The four-agent pipeline is too slow and expensive for chat, so each question gets one call (900-token output cap, low reasoning) over deterministically retrieved evidence. The model can't call tools or choose sources.
- **Grounding reuses the agents' rules.** Numbers must come from cited evidence, `risky_language` blocks odds, guarantees and sponsorship claims, and citations must be retrieved ids. There is one repair call, then a deterministic sourced fallback, so unverified prose is never shown.
- **No server-side chat storage.** History is supplied by the browser (sessionStorage) and bounded. That is enough for multi-turn follow-ups and avoids storing personal conversations.
- **Mock mode** (`AC_COPILOT_MODE=mock`) allows full-UI testing without paid calls.

## ADR-023 — Supplementary evidence layer (Step 14, 2026-10-23)
- **Separate store.** Official extras and secondary figures live in `data/programs/supplementary.json`, not in the agents' core store, so a third-party value can never overwrite an official one. The UI shows both, labeled by source type (official or secondary) and kind (published, reported or estimate), with the academic year and its basis.
- **Independent validation.** Each value is checked against the live raw page by deterministic code: identity and domain, the value near a context word, same-row matching for tables, and dates. Collector or model-assisted research is never trusted on its own.
- **Comparability.** The official affordability comparison is unchanged. An estimate can add a separately labeled estimated gap, but only for an academic-year estimate and a per-year budget, and never for estimates that may use in-state rates.
- **Copilot.** Retrieved facts carry their kind. Grounding rejects any sentence that cites an estimate without calling it an estimate, or that calls it official.
