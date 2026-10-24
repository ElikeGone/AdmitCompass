# AdmitCompass — Product Spec (v0.1, Step 1)

## 1. Core user journey
1. **Intake** — user enters a minimal profile: degree(s) and field, GPA band, years/type of work experience, target career(s), target geography, citizenship (country only), budget band, test status (none / GMAT / GRE + score band), timeline.
2. **Career framing** — system restates target careers as concrete roles and the program types that typically feed them.
3. **Program shortlist** — 3–8 programs ranked by career fit (not prestige), each with evidence cards.
4. **Program deep-dive** — requirements, STEM designation, outcomes, sponsorship evidence, cost; each claim labeled and sourced.
5. **Test decision** — GMAT vs GRE vs waiver vs none, with rationale.
6. **Skeptic review** — challenges shown alongside recommendations; weak items downgraded or flagged.
7. **Gap analysis & weekly plan** — prioritized gaps and a week-by-week action plan to deadlines.
8. **Journey roadmap** — timeline from today to enrollment, with human-decision checkpoints.
9. **Run trace** — which agents ran, tools called, sources used, tokens, cost, latency.

## 2. Features (MVP)
| Feature | Output |
|---|---|
| Profile intake | Validated `ApplicantProfile` |
| Career-first matching | Ranked `ProgramMatch[]` with fit rationale |
| Program verification | `ProgramFacts` with per-claim evidence |
| STEM / work authorization | `StemAssessment` (Verified / Unverified / Not STEM) |
| Outcomes & sponsorship | `OutcomesEvidence` (employers, roles, sponsorship evidence level) |
| Test guidance | `TestRecommendation` |
| Gap analysis + plan | `GapReport`, `WeeklyPlan` |
| Skeptic | `Critique[]` linked to specific claims |
| Roadmap | `JourneyRoadmap` |
| Observability | `RunTrace` (steps, tokens, cost) |

## 3. Agents (revised Step 2 — see decisions.md ADR-007)
All agents run on `gpt-6-luna` via Portkey. Code orchestrator + 4 agents:

| Agent | Responsibility | Output |
|---|---|---|
| **Orchestrator (code)** | Sequence, schema validation, evidence gates, input sanitizing, cost cap, trace | `RunTrace` |
| **Pathway Matcher** | Goals → roles → career-fit shortlist | `PathwayPlan` |
| **Evidence Analyst** | Requirements, STEM, outcomes, sponsorship, affordability; labeled & sourced | `ProgramDossier[]` |
| **Strategy Planner** | GMAT/GRE guidance, gaps, weekly schedule, roadmap | `ActionPlan` |
| **Skeptic** | Challenges weak claims; triggers ≤1 revision | `Critique[]` |

## 3b. Evidence layer (implemented Step 4)
- `backend/app/tools/evidence_store.py` is the only way agents get program facts: `list_programs`, `get_program`, `get_fact` (value + evidence + source label + freshness), `filter_programs` (unknowns excluded unless `include_unknown=True`), `evidence_for_claim`, `validate_claim`.
- Each of the 13 fields per program is either `verified` (value + evidence id that points to an accessed source) or `unknown` (value None, with a note).
- Sponsorship must be employer-specific; it is unknown for all 6 programs. STEM notes state that designation does not guarantee any immigration benefit.
- Freshness: data older than `ADMITCOMPASS_SOURCE_STALE_MONTHS` (18) is flagged with its period.

## 3c. Web application (implemented Step 6)
- Routes: `GET /health`, `GET /api/config`, `GET /api/fixtures`, `GET /api/demo`, `POST /api/runs`, `GET /api/runs/{id}?since=n`, and `/` (SPA) with `/static/*`.
- Views: Overview → guided profile (Background, Career goal, Location & budget, Tests & timeline, Review) → live run monitor (real backend events) → results (Programs, Strategy & plan, Skeptic & risks, Agent trace & usage). Result tabs are deep-linkable (`#/results/demo/strategy`).
- Budget can be entered per year or for the whole program; whole-program budgets are divided by 2 and that assumption is stated in the profile notes.
- Free-text fields (fit rationale, tradeoffs) that the model prefixed with "verified_fact" are shown with the weaker label "From sources", because they are not evidence-linked claims.

## 3d. AdmitCompass 2.0 (Step 8)
- **Design:** hybrid — editorial landing, conversational onboarding, interactive discovery and results; evidence and agent detail on demand. See `docs/redesign_plan.md`.
- **Two tiers of programs:**
  - *Full evidence* (6, evidence store): 13 facts each, per-fact sources. The only tier the agents use.
  - *Discovered* (24, `data/discovery/`): existence, name, location and provenance only, status `needs_verification` or `not_confirmed`. No cost, outcome, STEM or sponsorship fields (the schema forbids them). Never promoted automatically.
- **Catalog** (`backend/app/tools/catalog.py`): deterministic merge (the verified record wins on a name or .edu-domain match), search, filters (state, STEM-verified, max verified cost), and sorts where grounded (unknown cost always last). `GET /api/programs`.
- **Routes:** `#/`, `#/start`, `#/explore`, `#/how`, `#/results/:id/{shortlist|plan|evidence}`, `#/run/:id`.

## 4. Claim labeling (mandatory on every output claim)
- `verified_fact` — requires `source_url`, `source_title`, `retrieved_date`, quoted/summarized `evidence`.
- `inference` — reasoning from facts; must cite which facts.
- `unknown` — explicitly stated when evidence is missing.
- `advice` — recommendation; must reference supporting claims.

## 5. Verification requirements
- STEM designation is `verified_fact` only if an official school/DHS-CIP-aligned source says so; otherwise `unknown`.
- Employer sponsorship is never asserted from employer reputation; requires program- or employer-specific evidence; reported as an evidence level, not a promise.
- Sources older than a set threshold (e.g., 18 months) are flagged as possibly stale.
- Skeptic must review every recommendation; unresolved high-severity critiques are shown to the user.
- Deterministic tests: fixed profiles + fixed evidence snapshots → schema-valid, label-complete outputs.

## 6. Safety & privacy boundaries
- Collect minimum data: no names, emails, passport/ID numbers, exact birthdates; citizenship as country only.
- No persistence of profiles by default; session-only.
- No admission probabilities, no guarantees of admission or sponsorship.
- Not legal/immigration advice; visa items point to official sources and DSOs/attorneys.
- Human-judgment checkpoints flagged before applying, paying deposits, or committing to visa paths.
- API keys only via environment variables.

## 7. Explicit non-goals (MVP)
Admission probability scores; admissions committee simulator; essay writing; visa application help; networking, recruiting, casing, event planning; broad web crawling of all programs.
