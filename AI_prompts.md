# AI Prompt Log — AdmitCompass (MGT 409 Final Project)

Tool: Claude Code (Claude Opus 5.5). Each step logs the prompt given and a summary of the AI's output.

## Step 1: Foundation and Requirements — 2026-10-23

### Prompt
> We are starting my MGT 409 AI Foundations for Managers final project, called AdmitCompass. I want to build it with you step by step, and I will review your work after every major step. Do not build the full application yet.
>
> PROJECT CONCEPT — AdmitCompass is a career-first AI graduate education advisor, especially for international applicants. It should help applicants evaluate whether a graduate program realistically supports their intended career, given their background, goals, finances, citizenship, and work authorization constraints.
>
> Our distinctive feature is a Career Pathway Intelligence Engine that connects: applicant profile, education, experience, citizenship, budget, and career goals; career-first school/program matching; verified program fit and admissions requirements; STEM designation and work authorization considerations; employment outcomes and employer sponsorship evidence; GMAT/GRE decision guidance; applicant gap analysis and prioritized weekly action plan; a Skeptic/Devil's Advocate agent that challenges weak recommendations; an end-to-end applicant journey roadmap.
>
> Do not implement unsupported admission probabilities, guarantees of admission or sponsorship, or a redundant admissions committee simulator. Essays, visa application assistance, networking, recruiting, casing, and event planning are future phases, not MVP priorities.
>
> IMPORTANT PROJECT PRINCIPLES: 1. Real working application, not a static mockup or generic chatbot. 2. Multiple purposeful AI agents with distinct responsibilities, tools, and observable outputs. 3. Recommendations must distinguish verified facts, inference, unknowns, and advice. 4. Important factual claims must retain source URLs, dates, and evidence. 5. Never assume a program is STEM-designated or that an employer sponsors international applicants without adequate evidence. 6. Protect user privacy, minimize personal data, and require human judgment for consequential decisions. 7. Design for testability, reproducibility, cost/token measurement, and a polished user experience. 8. Prioritize a functioning, demonstrable MVP before optional features.
>
> THIS IS STEP 1 ONLY: FOUNDATION AND REQUIREMENTS. Inspect the working directory; if the professor's handout/rubric is present, extract exact requirements and points; otherwise create a labeled placeholder and report it missing. Then: A. folder structure; B. README.md; C. docs/product_spec.md; D. docs/rubric_tracker.md; E. docs/build_plan.md (deadline October 26, 2026); F. docs/decisions.md; G. AI_prompts.md logging this prompt; H. .gitignore and .env.example with safe placeholders. Propose a tech stack and explain; don't install dependencies or scaffold. Report files, tree, missing inputs, stack/agent architecture, checklist; stop for approval. Do not initialize git, publish, make external API calls, or build agents.

### AI output summary
- Inspected `project/` (empty) and parent folder; **no official handout/rubric found** → created `docs/rubric/OFFICIAL_RUBRIC_MISSING.md`.
- Created folder structure, README, product spec, rubric tracker (no invented criteria), build plan, decision log (ADR-001–005), this log, `.gitignore`, `.env.example`.
- Proposed stack: Python + FastAPI + Pydantic + Anthropic SDK, lightweight HTML/JS frontend, pytest, JSON evidence store; 7 agents + custom orchestrator.
- No dependencies installed, no git, no API calls.

## Step 2: Align to Official Requirements — 2026-10-23

### Prompt
> We now have the official MGT 409 final project requirements: https://zlisto.github.io/mgt_409_fa26/project_requirements.html. This is Step 2 of AdmitCompass. Read the complete official page, including grading, report, slides, model/budget, and testing instructions. Update our existing foundation to match the professor's requirements exactly. Do not build the application yet.
>
> 1. Replace the missing-rubric placeholder with the actual official 100-point rubric: Novelty + real-world value 21; app works 15; teaching staff can run it 5; look + feel 10; motivation + what is new 8; agent design 10; tokenomics 8; safety 8; impact + metrics 5; report design 2; slides content 6; slides design 2.
> 2. Update docs/rubric_tracker.md so every criterion has its exact points, required evidence, implementation plan, evidence file location, and status (pending/in progress/verified). Do not claim any evidence exists unless you inspect it.
> 3. Update docs/build_plan.md to prioritize a working, genuinely differentiated MVP and leave time for measured runs, safety tests, user testing, and final deliverables before Monday October 26, 2026 at 6 PM.
> 4. Correct the model plan: use the course PORTKEY_API_KEY with gpt-6-luna only. Claude Code is our development assistant, not necessarily the model running in our app. Do not use the Anthropic SDK or Anthropic API in the application unless I explicitly approve paying for a personal key.
> 5. Plan environment loading from both the project root and its parent folder, as the grader requires. Include a future fresh-clone test with the .env one level above the repo. Keep the setup achievable within 10 minutes.
> 6. Add explicit deliverables to the plan: public GitHub repo with README and .env.example; self-contained report.html of 10–15 printed pages with the professor's sections in exact order; self-contained reveal.js slides.html of at most 10 slides; optional 2–3 minute demo video. Images and screenshots must remain visible when the HTML files are opened separately.
> 7. Preserve our finalized product scope: Career Pathway Intelligence Engine, international applicant profile, career-first matching, verified program and STEM facts, sponsorship evidence, affordability, outcomes, GMAT/GRE guidance, gap plan, weekly action schedule, Skeptic/Devil's Advocate, and journey roadmap. No redundant admissions committee simulator or unsupported admission or sponsorship guarantees.
> 8. Review whether seven agents are actually justified. Propose a lean orchestration design with purposeful tool use, meaningful handoffs, structured outputs, a visible trace, source evidence, and a cost budget. Explain what each agent uniquely contributes. Do not implement yet.
> 9. Create an evidence capture plan covering: competitor comparison, one complete real agent trace with screenshots, actual input/cached/output tokens and costs, cost-reduction experiment with quality comparison, a tested safety defense, and real-user feedback or a timed baseline comparison. Never fabricate evidence.
> 10. Update AI_prompts.md with this Step 2 prompt, and docs/decisions.md with any changed architecture decisions. Verify the files you change.
>
> Return a concise report: exact files changed, official rubric coverage, revised technical architecture, critical path, unresolved risks, and what Step 3 should implement. Stop and wait for approval. No installation, API calls, git initialization, or full application scaffolding yet.

### AI output summary
- Fetched the official requirements page (one read-only web fetch); saved to `docs/rubric/official_requirements.md`; removed the missing-rubric placeholder.
- Rubric tracker rebuilt: 12 rows, 100 points, all `pending` (no evidence exists yet).
- Model switched to `gpt-6-luna` via Portkey (OpenAI-compatible SDK, pattern from hw3); Anthropic API removed from the app plan (ADR-001, ADR-004).
- `.env` loading from repo then parent (ADR-006); `.env.example` updated.
- Agents reduced from 7 to 4 + code orchestrator (ADR-007).
- Build plan rewritten to the Mon 6 PM deadline with an internal Mon 2 PM target; new `docs/evidence_plan.md`.

## Step 3: Backend Foundation and Model Smoke Test — 2026-10-23

### Prompt
> Step 3 for AdmitCompass: implement and verify the minimal backend foundation and one real model smoke test. Work in the existing project folder. Do not build the agents, program dataset, or UI yet.
>
> First, read the current README, product spec, build plan, decisions, rubric tracker, and official requirements. Do not overwrite earlier decisions without explaining why.
>
> 1. Create requirements.txt with only the Python packages needed for FastAPI, Pydantic validation, environment loading, the Portkey-compatible OpenAI SDK, and pytest. Use a virtual environment and install the dependencies.
> 2. Implement a robust environment loader that looks for .env in the project root first and then one folder above. Respect an already-set PORTKEY_API_KEY. Do not read, display, log, or commit the actual key. If missing, fail with a clear safe message. The grader will place .env above the cloned repository.
> 3. Implement a small Portkey client using only the course-authorized model gpt-6-luna. Do not silently substitute gpt-5.6-luna, Claude, or another model. Confirm the correct Portkey endpoint and API format from known working project configuration or official documentation; don't guess.
> 4. Create Pydantic schemas for Evidence and Claim. A verified claim must have a source URL and verification date. Support separate labels for verified fact, inference, unknown, and advice. Reject invalid verified claims.
> 5. Implement a token usage logger that records model, timestamp, input tokens, output tokens, cached input tokens when explicitly reported, elapsed time, and estimated cost only if supported by a documented price. Mark missing values unknown; do not invent token counts or prices. Never log keys or raw sensitive applicant information.
> 6. Create a minimal FastAPI app with /health returning safe status information. Include a minimal /api/smoke-test only if it is protected against unrestricted repeated calls; otherwise use a CLI smoke-test script so the API key cannot be abused through a public endpoint.
> 7. Make one minimal real API call using gpt-6-luna that returns a structured sample response, validates against Pydantic, and records actual usage. Do not use real applicant personal data. If the model is unavailable, stop, preserve the exact sanitized error, and ask me before changing models or API configuration.
> 8. Add tests for environment lookup, missing key, valid/invalid verified claims, and usage logging. Run them and report exact pass/fail results.
> 9. Update README with verified setup and commands. Update docs/decisions.md, docs/rubric_tracker.md, and AI_prompts.md. Save sanitized smoke-test evidence in experiments/ or tests/ so we can cite it in the final report.
> 10. Before finishing, verify that .gitignore excludes .env, keys, caches, and virtual environments. Do not initialize git, commit, or push.
>
> Report the actual files created, exact commands tested, model connectivity result, schema validation results, token usage fields returned, test results, and any blockers. Distinguish actual verification from plans. Stop and wait for my review before Step 4.

### AI output summary
- Built `.env` loader (repo → parent, env vars win, model locked to gpt-6-luna), Portkey client (config from hw3), Claim/Evidence schemas, usage logger, `/health`, CLI smoke test.
- pytest: 19/19 passed (after fixing one variable-name bug the tests caught).
- Real call succeeded: model `gpt-6-luna-2026-09-22`, 523 input / 0 cached / 123 output tokens, 5.2 s, cost unknown (no documented price). Output validated against Pydantic.
- Evidence: `experiments/smoke_test/`. No git, no commits.

## Step 4: Source-Verified Program Dataset and Evidence Retrieval — 2026-10-23

### Prompt
> Step 4 for AdmitCompass: build the source-verified program dataset and evidence retrieval layer. Work within the existing project. Read the product spec, official requirements, decisions, and current schemas first. The goal is to create a small, credible dataset that our agents can actually use. Do not build the agents or frontend yet.
>
> 1. Start with six full-time US MBA programs: Yale SOM, Harvard Business School, MIT Sloan, Chicago Booth, Duke Fuqua, and Rice Jones. These provide meaningful contrasts in career paths, cost, geography, and industry access. If an official source is inaccessible, record the field as unknown instead of guessing.
> 2. Use official university admissions, program, tuition, STEM, and employment-report pages as the primary sources. Collect current data only where directly supported. For each program, try to capture: university and program name, degree, location, duration; application requirements and standardized-test policy; tuition and published cost of attendance, including academic year; STEM designation with an explicit official source, or unknown; employment outcomes with cohort/year and metric definition; industry and function breakdown where available; published international student employment information; official source URL, page title, date checked, and evidence excerpt or short paraphrase.
> 3. Create structured JSON program records and a separate source registry under data/. Use stable program and evidence IDs. Do not fabricate admissions rates, scholarship odds, sponsorship policies, employment figures, or costs.
> 4. Treat sponsorship as a separate evidence category. A school's employment report or a company appearing in an employer list is NOT proof that the employer sponsors visas. If no reliable employer-specific sponsorship evidence is available, mark sponsorship as unknown. Clearly distinguish STEM designation from eligibility for any particular immigration benefit.
> 5. Build a deterministic evidence retrieval module with functions to list programs, retrieve one program, filter by program attributes, and return the supporting evidence for a claim. All program facts used by future agents must come through this module, not from invented model knowledge.
> 6. Extend the existing Pydantic schemas to validate program records, source references, numeric units, academic years, missing values, and evidence links. Reject malformed records and claims whose evidence IDs do not exist.
> 7. Add a source quality and freshness mechanism. Official university sources should be labeled as such, and older data should display its publication year and a freshness warning when appropriate. Do not imply a source was verified if it was not actually accessed.
> 8. Create tests for: valid and invalid program records; missing STEM status; unknown sponsorship status; evidence ID linkage; costs with correct academic years; employment outcome definitions; retrieval and filtering; protection against unsupported verified claims.
> 9. Save a source verification audit in experiments/source_audit.json with each program, URLs actually checked, which fields were verified, which remain unknown, and any inaccessible sources. Include source coverage statistics derived from the actual records.
> 10. Update README, product_spec, rubric_tracker, decisions, and AI_prompts.md with what was actually implemented and tested.
>
> Important: Keep the dataset deliberately small but credible. No fake data disguised as verified facts. Do not use applicant personal information. Do not call the LLM to invent missing school facts. No agents, UI, or GitHub push in this step. If web access is unavailable, build the schema and retrieval layer, mark unverified fields unknown, and report the source collection blocker instead of inventing verification.
>
> At the end, report the exact files created or changed, each program's verified versus unknown fields, actual source URLs, test results, source coverage, and remaining blockers. Stop and wait for my review before Step 5.

### AI output summary
- Six parallel research subagents collected evidence from official pages (raw notes in `data/sources/raw/`). The main session spot-checked 5 facts; all matched.
- Built `programs.py` schemas, `evidence_store.py` retrieval (freshness + source labels), and `scripts/build_dataset.py`. Generated `programs.json`, `source_registry.json`, and `experiments/source_audit.json`.
- Coverage: 49/78 fields verified (62.8%); 5 flagged values downgraded to unknown; sponsorship unknown for all 6; 30 of 49 logged URLs accessed.
- Tests: 48/48 passed.

## Step 5: Four Agents and Orchestrator — 2026-10-23

### Prompt (5a)
> Step 5 for AdmitCompass: implement the four purposeful AI agents and a working orchestrator using the existing verified program dataset. Read the current official requirements, product spec, decisions, build plan, schemas, evidence store, usage logger, and tests first. Do not build the frontend yet.
>
> GOAL: Given a fictional international MBA applicant profile, run an actual multi-agent analysis that produces career-first program recommendations, source-backed evidence, a realistic strategy plan, and a skeptical review. Save a reproducible trace showing what each agent did, which tools/data it used, and its measured token usage.
>
> 1. Build a structured ApplicantProfile schema covering education, experience, citizenship, target career/function/industry, location preferences, budget, academic background, test status, and time horizon. Minimize sensitive information and support missing/unknown values. Include at least two clearly fictional fixture profiles with meaningfully different career and budget constraints.
> 2. Implement four distinct model-powered agents, each with its own prompt and validated output: Pathway Matcher (maps career goals to plausible target roles and candidate programs, explains fit and tradeoffs, must use program IDs from the evidence store); Evidence Analyst (examines requirements, cost, STEM, employment metrics, sponsorship uncertainty, and source strength; retrieves actual evidence IDs and flags unsupported claims; distinguishes first-hand rechecked facts from other source-backed fields and summaries); Strategy Planner (test guidance, application gaps, prioritized weekly actions and a journey roadmap; no fabricated deadlines or guarantees); Skeptic (challenges unsupported conclusions, affordability assumptions, weak source evidence, incomparable employment metrics, and immigration/sponsorship claims; can request at most one revision of the relevant earlier work).
> 3. Implement a code orchestrator that passes structured outputs between agents, logs every handoff, enforces a bounded sequence and a single revision limit, and returns one final structured RecommendationReport. The orchestrator itself is not an AI agent.
> 4. Enforce grounding in code, not just prompts. Program IDs and evidence IDs must exist in the local evidence store. A verified claim must be supported by the referenced evidence. Unknown STEM/sponsorship values must remain unknown. Employment metrics with different definitions or cohort years must not be compared as if equivalent. Never invent admissions odds or visa eligibility.
> 5. Implement meaningful evidence-store tool calls with logs showing which agent requested which program/claim. Distinguish deterministic data retrieval from model reasoning. Do not allow model text alone to create new verified program facts.
> 6. Every agent should have a clearly scoped prompt and a validated Pydantic output. Implement safe parsing, bounded retries, error handling, and fail-closed behavior for missing evidence or invalid outputs. Prevent loops, excessive delegation, and unbounded spending.
> 7. Use only gpt-6-luna through the existing Portkey client. Reuse the usage logger and record per-agent input/output/cached tokens, latency, model name, and cost only when a documented price is available. Add a per-run request/token budget and show when the budget stops further calls. Do not invent pricing.
> 8. Save one actual end-to-end run on a fictional applicant, including: input fixture; each agent's validated output; chronological handoff/tool trace; Skeptic findings and whether a revision occurred; final recommendation report; usage and latency summary. Store sanitized evidence in experiments/agent_runs/. Never log keys or real applicant private information.
> 9. Add automated tests for schemas, valid handoffs, missing evidence, unsupported claims, mismatched employment metric definitions, one-revision limit, budget enforcement, agent failures, and reproducibility of the deterministic validation layer. Mock LLM responses for unit tests, then run exactly one real full-agent integration test if the initial tests pass.
> 10. Update README, docs/decisions.md, docs/rubric_tracker.md, docs/build_plan.md, and AI_prompts.md with what was actually done. Do not claim the rubric's agent-design evidence is complete until a real trace exists.
>
> Before finishing, report: actual files created/changed; the exact agent sequence and real tool calls; test results; real integration run success/failure; sample final recommendations and evidence IDs; Skeptic objections and any revision; per-agent tokens, total tokens and runtime; safety or grounding violations detected; unresolved blockers. Do not build the UI, publish to GitHub, or run repeated paid integrations. Stop and wait for my approval before Step 6.

### Output summary (5a)
- Built the applicant schema, 2 fictional fixtures, 4 agents, read-only tools, grounding checks, budget, and orchestrator; 72 mocked tests passed.
- The real run failed closed at request 1: Chat Completions does not allow function tools together with reasoning on gpt-6-luna. Asked the user how to proceed.

### Prompt (5b)
> Let's use the Responses API, but verify compatibility before rewriting the runner.
>
> First, run one minimal, inexpensive gpt-6-luna tool-calling test through Portkey's /v1/responses endpoint, using the existing key and a harmless local test tool. Preserve reasoning if supported. Do not expose the key or use real applicant data.
>
> If it succeeds:
> 1. Update the existing model adapter and agent runner to support Responses API tool calls and tool results correctly.
> 2. Preserve all four agents, their distinct tools, structured output validation, grounding rules, budgets, and the one-revision limit.
> 3. Ensure request limits and token usage are counted correctly across tool-call rounds, including reasoning tokens if reported.
> 4. Run all mocked tests and fix any regressions.
> 5. Run exactly one real end-to-end analysis on the fictional tech-PM applicant, provided tests pass.
> 6. Save the real agent trace, outputs, tool calls, Skeptic findings, latency, and actual token counts.
> 7. Update the Step 5 documentation and AI_prompts.md with the failure, fix, and verified results.
>
> If the minimal Responses API test fails, stop and show me the sanitized error. Do not switch models, turn off reasoning, or rewrite the full runner without asking.
>
> Do not build the frontend or push to GitHub yet. Report exact tests, actual model calls, results, and remaining blockers.

### Output summary (5b)
- The minimal Responses API tool test passed (2 requests, 209 tokens, reasoning effort low).
- Added a Responses adapter (stateless, encrypted reasoning passed back) and counting of reasoning tokens. Mocked tests passed.
- Real attempt #2 was rejected at request 1 (JSON mode requires the word "json" in the input; adapter fixed). Real attempt #3 ran 14 requests (96,055 tokens: 84,358 input, 57,724 of them cached, plus 11,697 output) and was stopped by the request budget at the Strategy Planner.
- The run exposed a grounding false positive (the applicant's budget number was rejected) and repeated tool calls. Both fixed with regression tests; budget defaults raised to 20 requests / 200k tokens. 78 mocked tests pass.
- No complete real end-to-end trace yet; one more paid run needs user approval.

### Prompt (5c)
> Yes, run exactly one more paid end-to-end analysis using the fictional tech-PM applicant and the fixes already implemented.
>
> Before running: 1. Confirm all 78 tests still pass. 2. Confirm the Responses API is using gpt-6-luna only, with reasoning effort low. 3. Confirm the 20-request, 200,000-token limits and one-revision limit are enforced. 4. Confirm no real applicant data or API keys will be written to the trace.
>
> Then run the analysis once. Do not automatically start another full run if it fails.
>
> Afterward: save the complete chronological trace, including all four agents, tool calls, handoffs, validation failures, and Skeptic findings; report whether the Skeptic requested a revision and whether it was completed; show the final recommended programs, career-fit reasoning, source IDs, affordability conclusions, and unknown sponsorship fields; report per-agent and total model requests, input tokens, cached input tokens, output tokens, reasoning tokens, runtime, and any known cost (do not invent pricing); verify that final recommendations cite real program evidence and that incomparable employment metrics are not presented as directly comparable; identify repeated or wasteful model/tool calls and opportunities to reduce tokens without weakening evidence verification; update the Step 5 documentation, rubric tracker, and AI_prompts.md with the actual outcome.
>
> If the run fails, preserve the sanitized error and partial trace, then stop and ask before another paid attempt. Do not build the UI or push to GitHub yet. Return the results for my review.

### Output summary (5c)
- Pre-checks passed (78 tests; gpt-6-luna, effort low; 20 requests / 200k tokens / 40 tools; 1 revision; fictional fixture; no key references).
- One paid run completed: `20261023T180104Z`, 16 requests, 105,041 input (64,600 cached) / 14,936 output (1,640 reasoning) tokens, 50.7 s, cost unknown. Shortlist: MIT Sloan, Booth, Fuqua, Yale SOM; sponsorship unknown for all; metrics marked not comparable; Skeptic made 1 medium finding and requested no revision.
- Added `scripts/verify_run.py`; the audit passed. Found likely Portkey response-cache replay of requests 1–13, a trace gap (first-pass violation details; now logged), and a false-positive "guarantee" flag. 79 tests pass.

## Step 6: Interactive Web Application — 2026-10-23

### Prompt
> Step 6 for AdmitCompass: build a polished, genuinely interactive web application around the existing working four-agent backend.
>
> Read the current README, official project requirements, product spec, agent schemas, orchestrator, run output, evidence store, and existing tests before making changes. Preserve the verified agent system and its grounding rules.
>
> Our objective is to make AdmitCompass feel like a premium career intelligence platform, not a generic chatbot or a static assignment demo. Prioritize a reliable, attractive, usable end-to-end experience that the professor can run locally within 10 minutes.
>
> DESIGN: Use a clean, premium SaaS aesthetic: warm off-white backgrounds, deep navy typography, restrained teal/blue accents, spacious cards, clear visual hierarchy, refined typography, subtle interactions, accessible contrast, and responsive layout. Keep the current FastAPI plus lightweight HTML/CSS/JavaScript architecture unless a compelling technical reason requires changing it. Avoid unnecessary dependencies and build complexity.
>
> CORE USER JOURNEY: 1. Welcome/dashboard (career-first value proposition, how it works, start a new assessment or load a fictional demo applicant, evidence-based and not admission guarantees). 2. Applicant profile (guided multi-step form; education, work experience, citizenship, target career, preferred industry/function, location preferences, budget and budget period, GMAT/GRE status, time horizon; validation, explanations, back/next, progress indicator; review and edit before running; no unnecessary sensitive identifiers). 3. Agent analysis (real FastAPI routes executing the existing orchestrator; four distinct agents with descriptions; truthful progress from actual backend events; chronological activity feed with tool calls, handoffs, evidence checks, warnings, and Skeptic findings; handle 30–120 second runs without freezing; prevent duplicate submissions and accidental repeated paid runs; token/request budget information and meaningful error states; never expose API keys or private model reasoning). 4. Recommendation dashboard (polished program cards with name, location, career-fit reasoning, STEM status, total cost and budget fit, employment data where comparable, sponsorship uncertainty; distinguish verified facts, inference, advice and unknowns; expandable source evidence with title, URL, publication year and verification status; missing or outdated data visually clear; no fabricated rankings, admissions chances, scholarship odds, sponsorship probabilities, or missing facts; meaningful comparisons without comparing incompatible employment metrics). 5. Career strategy (GMAT/GRE guidance, applicant gaps, prioritized actions, weekly action plan, journey roadmap; readable, interactive, specific; the Skeptic's critique and unresolved risks; decisions that require the applicant's own judgment). 6. Demo and evidence (clearly labeled demo mode using the saved successful fictional tech-PM run, a genuine saved output; distinguish viewing a saved run from starting a fresh paid analysis; support a second fictional applicant profile without inventing an AI analysis for it; a way to inspect the actual chronological agent trace; actual token counts and runtime for the saved run, with cost marked unknown unless a documented price is available).
>
> BACKEND AND SAFETY: only the API routes the UI needs (load demo, start an analysis, run status/events, results); safe background execution or another reliable nonblocking approach for a local single-user demo; server-generated run ids and bounded concurrent/duplicate runs; user input cannot override system prompts, models, budget caps, or evidence-store data; all secrets server-side; escape untrusted text in the frontend and never inject raw model output as HTML; no chain-of-thought or encrypted reasoning; handle API failures, timeouts, and budget stops gracefully.
>
> TESTING: tests for API validation, profile submission, run lifecycle, demo loading, duplicate-run protection, safe error handling, and evidence linkage; run all existing tests and fix regressions; start the real local server and test the website in a browser if automation is available; verify the full saved-demo journey from onboarding to recommendations, sources, Skeptic critique and roadmap; no paid model run just to test the UI — use mocks and the existing saved trace.
>
> DOCUMENTATION: update README with exact installation and startup commands and a short demo walkthrough; update product_spec, decisions, rubric_tracker, build_plan and AI_prompts.md; capture genuine screenshots of the working interface for the final report and slides.
>
> At the end, report: exact files created/changed; the URL to open locally; the tested user journey and what worked; backend endpoints added; tests passed/failed; screenshots captured; known UI bugs and remaining limitations; whether a fresh analysis can be initiated from the UI, without actually starting another paid run. Do not initialize git, push to GitHub, create the final report or slides yet. Stop and wait for my review before Step 7.

### Output summary
- Added `backend/app/runs.py` (background run manager, one active run, 3 per server), a rewritten `backend/app/main.py` (6 routes plus the SPA), and a time limit on the run budget. Secret redaction moved into the orchestrator after a test caught a possible key leak through error text.
- Built `frontend/index.html`, `styles.css`, `app.js`: overview, 5-step profile wizard with validation and review, paid-run confirmation dialog, live run monitor from real events, results dashboard with 4 deep-linkable tabs.
- Tests: 96 passed, 1 skipped (live). Browser-tested the saved-demo journey and the wizard. The live-run view was tested with a browser-only fetch stub that replays the saved events; no paid run was made.
- Fixed during browser testing: a JS syntax error, a native `append` array bug, misleading "Verified fact" chips on model free text, noisy freshness warnings, mobile nav overflow, the stale tab when opening new results, and the run heading after a stop.
- 8 screenshots in `deliverables/screenshots/` (README there explains how each was captured; 2 are clearly labeled UI-test stubs).

## Step 7: Safety, Tokenomics and Performance Experiments — 2026-10-23

### Prompt
> Step 7 for AdmitCompass: conduct rigorous safety, tokenomics and performance experiments using the existing working application and saved agent traces.
>
> Read the official rubric, evidence plan, existing experiments, real agent run, usage logger, safety code, source registry, and Step 6 app before proceeding.
>
> Our goal is to produce credible, reproducible evidence for the Safety (8 points), Tokenomics (8 points), and Impact + Metrics (5 points) rubric sections. Prioritize actual measured results over polished but unsupported claims.
>
> IMPORTANT: Do not run paid full-agent analyses without my explicit approval. Use saved traces, deterministic tests, mocked responses and local measurements first. If a real model experiment would materially improve the evidence, prepare the exact proposed test, expected token budget and justification, then ask me.
>
> PART A — SAFETY RED-TEAMING: at least 12 meaningful scenarios across prompt injection in profile fields; malicious instructions in untrusted program/source content; fabricated employer visa-sponsorship claims; STEM designation or immigration-benefit guarantees; fabricated admission probabilities or scholarship odds; unsupported program cost or employment numbers; employment statistics with incompatible definitions or cohort years; misleading affordability conclusions based on incomplete total costs; attempts to leak API keys or system instructions; attempts to exceed request, token, tool or time limits; malformed agent responses or missing evidence IDs; personally identifying or sensitive applicant data. For each test, record the scenario, entry point, expected safe behavior, actual behavior, pass/fail, and mitigation. Test actual application code. Use a clearly marked controlled test environment; do not place malicious content into the production dataset. Add regression tests for every discovered issue and fix serious failures.
>
> PART B — TOKENOMICS: analyze the saved real runs (requests and tokens per agent; input, cached, output, reasoning tokens; latency per agent and end-to-end; repeated tool calls and retry overhead; cache effects and why the replayed run is not a clean benchmark; cost unknown unless a documented gpt-6-luna price exists). Implement at least one meaningful cost-reduction improvement without weakening grounding. Compare baseline and optimized using the same deterministic scripted fixture and identical profile; measure serialized prompt sizes or tokenizer counts and distinguish estimates from provider-reported usage; compare completeness, grounding validity, tool calls, and validation behavior. Don't present mocked usage as billing. Document an authoritative price if found; otherwise formulas and clearly hypothetical scenarios.
>
> PART C — PERFORMANCE AND IMPACT: measure app startup, demo loading, evidence retrieval, API response time, and deterministic report verification with sample size, methodology, median and range. Design a 2–3 tester evaluation protocol (realistic task, ChatGPT/manual baseline, success criteria, time, usefulness and trust ratings, sponsorship-uncertainty and evidence-transparency questions). Do not invent users, feedback, times saved or satisfaction scores.
>
> PART D — FIX KNOWN ISSUES: fix the false-positive guarantee wording rule; audit budget-period handling (no silent ÷2; label approximations; show unknown when unsafe); ensure the UI distinguishes official sources, collector-backed facts, independently rechecked facts and paraphrases; ensure source data cannot become agent instructions; preserve existing tests and real-demo behavior.
>
> PART E — DELIVERABLES: safety_test_matrix, tokenomics_analysis, optimization_comparison, performance_metrics, user_test_protocol, and an evidence index under experiments/ and docs/. Update README, decisions, rubric_tracker, build_plan and AI_prompts.md. Run the full test suite, verify the saved demo still loads, and document any regressions.
>
> Report: safety tests attempted/passed/failed; vulnerabilities discovered and fixed; measured baseline vs optimized; whether quality and grounding were preserved; performance measurements; real user testing completed vs pending; all created evidence files; exact remaining rubric blockers; whether an additional paid experiment is worth doing, with a bounded budget. Do not start a paid run, push to GitHub, or create the final report/slides. Stop for review before Step 8.

### Output summary
- Safety: 24 red-team scenarios run against the real code in a controlled environment, 24/24 pass. Found and fixed 6 issues: sponsorship/STEM claims citing unrelated evidence, scholarship-odds language, whole-program budget ÷2, the guarantee false positive, injection relying only on prompt wording, and PII in free text. While fixing, caught and corrected an over-strict topic rule that would have dropped 3 correct hedged claims from the real demo.
- Tokenomics: real-run analysis (retry overhead 35% of input; cache replay is requests 1–9, correcting the earlier "1–13"). Price unknown; hypothetical scenarios only. Repair-mode retry + downgrade: 17→12 requests, −29.9% estimated input tokens in a deterministic replay, quality identical except the expected relabelling.
- Performance: startup 2.6 s median; API 2–7 ms median; dataset load+validation 8 ms; audit 0.7 s.
- User testing: protocol and form ready; 0 sessions. Tests: 124 passed, 1 skipped. No paid calls.

## Step 8: AdmitCompass 2.0 — Hybrid Product Redesign + Discovery Foundation — 2026-10-23

### Prompt
> STEP 8 — ADMITCOMPASS 2.0: HYBRID PRODUCT REDESIGN + DISCOVERY FOUNDATION. We are changing direction based on actual product feedback. The existing AdmitCompass application feels visually overcrowded, its typography is not pleasing, and the six-school limit makes the product feel too constrained. Our chosen design direction is HYBRID: elegant, editorial landing page; clean, simple and welcoming onboarding; modern, interactive program discovery and career results; powerful evidence and agent details available on demand, not dominating the interface. Read the existing application, product spec, official rubric, tests, saved demos and decisions before changing anything. Preserve the working backend, all four agents, grounding, budgets, safety rules and saved traces.
>
> PHASE A — AUDIT: inspect current screens, identify sources of visual overload, record a concise before/after plan in docs/redesign_plan.md, then implement it.
> PHASE B — DESIGN SYSTEM: warm ivory #F8F7F3, deep navy #18283D, muted teal #397F79, soft sage #E7EBE7; Instrument Serif for selective editorial headings; DM Sans for body, navigation, forms and cards; reliable local fallback fonts; consistent spacing, type scale, buttons, form controls, cards and breakpoints; avoid excessive gradients, shadows, borders, badges and dashboard clutter.
> PHASE C — JOURNEY: 1. landing (career-first headline, short explanation, one prominent CTA, how it works, secondary saved demo); 2. onboarding (conversational focused steps, progress, examples, fewer fields at once, review/edit, clear budget-period choices); 3. Explore Programs (search, filters, sorting where grounded, readable cards; discovery central); 4. recommendations (why each program fits the intended career, cost and budget status, STEM evidence, most important uncertainty; expandable sources and advanced comparisons); 5. roadmap (next three priority actions first, then full plan and checklist); 6. transparency (agent trace, tokens, logs, citations, Skeptic review in a secondary How AdmitCompass Works / Evidence & Risks area); 7. mobile (common narrow widths, no horizontal overflow or inaccessible controls).
> PHASE D — DISCOVERY FOUNDATION: keep the six verified programs as a curated evidence-backed collection but not the whole universe; a separate discovered-program schema (provenance URL, discovery date, degree type, program name, university, location, verification status); deduplication and safe merging; deterministic filtering and search; a clear Needs verification state; no fabricated tuition, employment, STEM, admissions odds or sponsorship; no automatic promotion to verified. Investigate one practical, trustworthy method of finding additional real US MBA programs from official pages or a reputable directory; document source, access limits, coverage and maintenance. If reliable retrieval is available, implement a modest real source-backed discovery index labelled discovered; otherwise finish the architecture and explain the blocker. Don't claim live search unless it is; say so if it's a periodically built index. Don't feed discovered facts to the agents as verified evidence.
> PHASE E — TESTING: preserve tests; add tests for discovery schema, provenance, dedup, unknown fields, safe merging and verified-vs-discovered separation; browser-test the redesigned journey; verify the saved applicant A demo and its citations; responsive and keyboard checks; genuine screenshots; no paid calls.
> PHASE F — DOCUMENTATION: update README, product_spec, decisions, rubric_tracker, build_plan and AI_prompts.md; document what works versus planned.
>
> Report: screens redesigned and key UX changes; fonts and design system; screenshots and browser-test results; how many real programs were discovered; discovery sources and limitations; what discovered programs can and cannot be used for; tests and regressions; remaining work to integrate discovery into recommendations; exact files changed. No paid run, final report, slides or GitHub push. Stop for review.

### Output summary
- Audit + plan: `docs/redesign_plan.md`. New design system and self-hosted fonts. Rewrote `frontend/index.html`, `styles.css`, `app.js`: landing, 5-step onboarding + review, Explore programs, Shortlist / Roadmap / Evidence & risks, How it works, calmer run screen.
- Discovery: `DiscoveredProgram` / `DiscoveryIndex` schemas, `Catalog` merge/search, `GET /api/programs`, `scripts/build_discovery_index.py`, `data/discovery/` (24 real programs, 21 confirmed on fetched official pages, 3 not confirmed). AACSB directory evaluated as a future seed list.
- Tests: 151 passed, 1 skipped (26 new discovery tests + an append-safety guard). Browser-tested all routes at 1024/375/320 px with no horizontal overflow; keyboard (skip link, Esc closes the dialog, focus return). Saved demo citations resolve (29 sources).
- Bugs found in testing and fixed: hero gutters lost, native append stringifying arrays/null (3 places, now prevented by a put() helper + test), legacy demo profile showing "no budget", a stale search-response race, the nav label wrapping at 320 px, dialog focus not returned.

## Step 9: Homepage + Explore Programs from a Visual Reference — 2026-10-23

### Prompt
> I've attached a visual reference for the AdmitCompass website redesign. The current website is not meeting my expectations. It looks like a text-heavy academic report rather than a polished, modern AI platform. I want a significant improvement in visual quality, usability, and interactivity.
>
> Use the attached screenshot as the PRIMARY VISUAL REFERENCE for the homepage and overall design direction. IMPORTANT: The screenshot is a visual concept, not a finished specification. Do not simply reproduce it as a static image. Build real, functional HTML/CSS/JavaScript components. Match its overall visual quality, typography hierarchy, spacing, color balance, layout composition, and professional appearance. Preserve the existing working backend, four agents, safety controls, evidence system, and saved demo. Do not copy invented statistics, program counts, photos, or unsupported claims from the reference image. Do not claim capabilities that the backend doesn't actually support.
>
> FIRST IMPLEMENTATION MILESTONE — ONLY TWO SCREENS:
> 1. HOMEPAGE: clear branding and navigation; a compelling career-first headline; a visually engaging hero; professional imagery or an equally strong visual composition; clear CTAs (Get My Recommendations, Explore Programs); a concise explanation of how AdmitCompass works; a dedicated value proposition for international applicants; thoughtful hover states, transitions, and mobile navigation.
> 2. EXPLORE PROGRAMS: search by school, program, location, and relevant career keywords; filters based only on available, grounded program data; sort options with transparent criteria; visually attractive, compact school cards; a clear distinction between evidence-backed and newly discovered programs; functional View Details actions; save and compare if feasible without breaking existing architecture; honest unknown states for missing cost, STEM, employment, and sponsorship information.
>
> DESIGN EXPECTATIONS: hybrid premium editorial + modern SaaS aesthetic; stronger typography and more deliberate hierarchy; much better use of whitespace and visual balance; a professional, attractive, consistent palette; responsive desktop and mobile layouts; accessible contrast, keyboard navigation, readable font sizes; no excessive text walls or repetitive oversized cards; no fake buttons or decorative interactions that do nothing.
>
> Before coding, briefly describe how you will translate the reference into functional components. Then implement both screens and test them in a real browser. Capture screenshots of the new homepage and Explore Programs page at desktop and mobile widths. Run the existing tests and verify the saved demo still works. DO NOT redesign the remaining screens yet. DO NOT make paid AI calls. DO NOT start the final report or slides. DO NOT push to GitHub. Stop after these two screens and show me the results for approval.

### Output summary
- Homepage: new header + mobile menu, editorial hero with an original SVG illustration and live counts (6 / 24 / 4), feature row, how-it-works (4 steps), international-applicant section, sample preview card (real values from the saved run), closing CTA band.
- Explore: grounded career-keyword search, filters, sort with the criterion explained on screen, compact monogram cards with honest chips, a View-details drawer (new `GET /api/programs/{id}`), Save (localStorage) and Compare ≤3 with unknowns. 3 new tests; 154 pass.
- Browser-tested at 1440 / ~1024 / 375 px: menu (open, Esc, close on navigate), search, filters, sort, save, compare cap, drawers (Esc + focus), no overflow. Fixed during testing: nav wrapping at mid widths, hero art overlapping copy, mobile hero stacking, monogram initials. Headless Edge can't capture true phone widths (minimum ~500 px), so the mobile screenshots come from the browser pane.

## Step 10: AdmitCompass 4.0 — Modern AI Startup Visual Reset — 2026-10-23

### Prompt
> (The user attached a design brief with reference images and specified: Direction A "Modern AI Startup"; Plus Jakarta Sans for headings and Inter for body; white #FFFFFF, canvas #F5F7FB, navy #0F172A, blue #2563EB, teal #14B8A6; remove Instrument Serif, thin academic headings, beige backgrounds, the campus illustration and oversized text-heavy cards. Homepage headline "Your career ambition deserves a better education plan." with a working preview of the fictional applicant's career pathway and recommendations.)
>
> ADMITCOMPASS 4.0 — MODERN AI STARTUP VISUAL RESET. CONTEXT: The user has rejected the previous academic/editorial design. The thin serif typography, cream-colored background, campus illustration, and brochure-like appearance do not meet expectations. This is not a request for minor CSS polishing. We need a clearly different visual identity that feels like a modern AI software product.
>
> DESIGN SYSTEM — REQUIRED: Headings Plus Jakarta Sans; body/interface Inter; no serif fonts anywhere in the user-facing experience; main background #FFFFFF; secondary surfaces #F5F7FB; primary text #0F172A; primary accent #2563EB; supporting accent #14B8A6; secondary text #475569; rounded corners around 12–16px; consistent spacing, accessible contrast, clear focus states; strong typography hierarchy and comfortable reading sizes; restrained shadows and subtle, purposeful motion. REMOVE: Instrument Serif and the old serif font stack; cream/beige-heavy identity; decorative campus hero illustration; thin editorial headings; repetitive oversized text cards; excessive badges, tiny labels and dense technical content.
>
> IMPLEMENT ONLY TWO SCREENS. SCREEN 1 — HOMEPAGE: modern branding and navigation; hero headline "Your career ambition deserves a better education plan."; supporting copy about career-first program discovery, verified information and actionable guidance; primary CTA Find My Pathway; secondary CTA Explore Programs; a visually compelling, interactive product preview using real saved fictional-applicant data; a career pathway preview (background → education options → target role); one or two authentic program insights from the saved analysis; short How It Works; clear international applicant value proposition; responsive layout and polished mobile navigation. Do not use a static dashboard screenshot as the entire hero; build functional components. SCREEN 2 — EXPLORE PROGRAMS: preserve the existing 30-program index (6 evidence-backed, 24 discovered); prominent search; clean filter controls; active filters and reset; responsive program cards; clear verification status; verified cost/STEM/outcome facts only when supported; explicit unknown states; save programs; compare up to 3; functional details and source links; clear distinction between evidence-backed and newly discovered programs; smooth, purposeful interactions. Do not fabricate career-fit scores, employment outcomes, costs, sponsorship facts, school imagery, or program coverage.
>
> QUALITY REQUIREMENTS: preserve the backend, four agents, evidence store, safety checks, API contracts and saved demos; don't migrate frameworks unnecessarily; test at 1440, 1024, 768 and 375 px; verify navigation, search, filters, save, compare, details, keyboard access and mobile menu; verify the new fonts load and no serif font remains; verify no horizontal overflow; run the automated tests; capture genuine desktop and mobile screenshots. ACCEPTANCE TEST: recognizably different from the previous academic design — a contemporary AI startup, not a university brochure with blue buttons. REPORT: what changed visually and functionally; screenshots; browser interactions verified; test results; known limitations; files changed. Do not redesign other screens, make paid calls, create report/slides, or push. Stop for visual approval.

### Output summary
- New identity: self-hosted Plus Jakarta Sans + Inter; serif fonts and the campus SVG deleted; global tokens switched to the white/navy/blue/teal palette (other screens inherit the fonts and colours, layouts unchanged).
- Homepage: product-led hero with the requested headline (gradient accent), Find my pathway / Explore programs, and an interactive preview driven by `/api/demo` (pathway with clickable MBA options and real per-program insight; shortlist with cost-vs-budget bars; next three steps). How it works (4 cards), international applicants (4 features), dark closing CTA.
- Explore: rebuilt UI on the unchanged API — search, filters, active chips + reset, cards with cost/STEM/employment strip and explicit Unknowns, status for full evidence / needs verification / page not retrieved, save, compare tray (≤3), details and compare drawers with source links.
- Verified at 1440/1024/768/375 px (no overflow; menu at ≤980 px with Esc and close-on-navigate; drawers with Esc and focus return); fonts confirmed loaded; 155 tests pass (new typography test); saved demo audit passes.

## Step 9B: Colour, School Verification and Link Repair — 2026-10-23

### Prompt
> (The user attached a design note asking for more colour — blue for primary actions, violet for AI insights, cyan for discovery, emerald for verified facts, amber for information that needs checking — and explaining that "Needs verification", "Page not retrieved" and "Unknown" mean different things, with a Discover → Retrieve → Extract → Validate → Publish verification workflow and a request to fix the links.)
>
> STEP 9B — ADMITCOMPASS 4.0: COLOR, SCHOOL VERIFICATION AND LINK REPAIR. The modern startup design is approved as the foundation, but the user wants more color and a much more complete program discovery experience. Two major issues: 1. The site still feels too white and visually repetitive. 2. Too many discovered schools display Needs verification, Page not retrieved, and Unknown, with limited useful information. This step must improve BOTH design quality and the underlying evidence. Do not simply remove warning labels.
>
> PART A — MORE COLOR: preserve Plus Jakarta Sans, Inter and the startup identity; controlled palette (blue #2563EB, violet #7C3AED, cyan #06B6D4, emerald #10B981, amber #F59E0B, navy #0F172A, white, canvas #F5F7FB) applied with restraint to the hero and section backgrounds, career pathway preview, navigation states, program cards, search/filter states, verification indicators, compare tray and details panel; accessible tints, not rainbow cards.
> PART B — AUDIT ALL 30 PROGRAM LINKS: check URLs, HTTP status, redirects and final destination; verify the page matches the program; identify broken, redirected, blocked, stale or incorrect URLs; prefer official pages; never invent replacements; record link_audit.csv (status, checked_at, original_url, final_url, program_id, issue, resolution); reasonable timeouts, concurrency and retries; no aggressive scraping or bypassing access controls.
> PART C — ENRICH DISCOVERED PROGRAMS: for the 24 discovered programs attempt official program name and degree, location, format and duration, admissions requirements and tests, tuition and/or cost of attendance with period and year, STEM where explicitly documented, employment outcomes with cohort and definition, published deadlines, and official source URLs and retrieval dates; start small, validate, then expand; every field with provenance; never fabricate, infer STEM from the degree name, or treat school-level outcomes as program-level; no sponsorship inference.
> PART D — EVIDENCE STATUS: Detailed evidence / Partially verified / Discovered / Retrieval unavailable; never "verified" just because a homepage loaded; never downgrade or overwrite stronger evidence with weaker scraped content; field-level provenance and safe promotion reusing existing validation.
> PART E — UX AND LINKS: official page from every details view; direct source links for each supported fact; plain-language explanation of failed retrieval with the confirmed official link; avoid repeated identical Unknown chips; don't hide uncertainty; distinguish Not checked from Checked but not established; no jargon.
> PART F — TEST AND DOCUMENT: test promotion, provenance, dedup, source relevance and non-overwrite rules, links and error states; browser-test colour and cards on desktop/mobile; preserve the four-agent workflow, saved demo and safety; run all tests; no paid LLM calls; no GitHub or report/slides.
>
> RETURN: updated screenshots; links checked/working/blocked/corrected; additional programs with supported facts; counts by evidence status; which fields remain unknown and why; test results; exact files changed; remaining blockers. Do not claim a program is verified unless its specific facts have adequate evidence. Stop for review.

### Output summary
- Link audit: 193 URLs across 30 programs; all 100 fact-source URLs reachable (10 via in-site redirects, now shown by final URL); 2 official program pages block automated access (Columbia, Michigan Ross); Kelley's page reachable despite the collector's earlier TLS error; 29 old guessed URLs (never used as evidence) are broken.
- Enrichment: 22 programs promoted (191 verified fields across 28 programs); 22 collector values downgraded after review; 7 enrichment facts re-checked by hand (6 matched; 1 mismatch caught: Cornell STEM). Status: 5 detailed / 23 partial / 1 discovered / 1 retrieval unavailable.
- UI: colour layer; Explore cards differ by evidence level; plain summaries instead of triple Unknowns; official page link on every card; details separate "Not published" and "Not checked yet"; legend drawer; evidence-status filter.
- Tests: 170 passed, 1 skipped; safety 24/24; demo audit ok.

### Prompt (2026-10-23)
> I prefer a darker background instead of plain why

### Output summary
- Added a dark theme layer (`frontend/styles-dark.css`) across all screens; fixed contrast of buttons, logo tiles and claim labels; fixed a repeating dropdown arrow. 170 tests pass. Screenshots: `deliverables/screenshots/v6-dark/`.

### Prompt (2026-10-23)
> Add a light/dark toggle in the header, remembered per browser, with dark as the default.

### Output summary
- Added a sun/moon toggle in the header (desktop and mobile), saved in localStorage, applied before first paint; dark by default. Browser-verified default, switch, persistence after reload, and mobile placement. 171 tests pass.

## Step 10: AdmitCompass 5.0 — Career Intelligence Dashboard — 2026-10-23

### Prompt
> STEP 10 — ADMITCOMPASS 5.0: CAREER INTELLIGENCE DASHBOARD.
>
> Build one cohesive dashboard with five sections:
> - **Career pathway:** background → education → target role; strengths vs AI-inferred gaps; an interactive shortlist.
> - **Program fit:** why it fits, the evidence and the unknowns; no match percentages or odds.
> - **Affordability:** budget and period vs verified costs; compare only compatible measures; deterministic gap, otherwise "Not enough comparable data"; source one click away; no invented scholarships.
> - **International feasibility:** verified STEM; official outcomes only; sponsorship unknown unless employer-specific; STEM ≠ sponsorship; no guarantees.
> - **Application workspace:** milestone cards; complete, undo and reset; local persistence; progress; next task; official deadlines only; saved programs.
>
> Keep the fonts and palette; make it responsive at 1440/1024/768/375 with reduced motion; reuse the APIs, demo and provenance; keep old routes; no paid calls, accounts or uploads. Test every value, budget edge cases, unknowns, persistence, keyboard and overflow, and take screenshots. Return the deliverables and stop for review.

### Output summary
- **Backend:** `backend/app/tools/dashboard.py` and `GET /api/dashboard/{run_id}`.
- **Frontend:** `#/dashboard/:id` view and `frontend/styles-dash.css`.
- **Tests:** `tests/test_dashboard.py` (10 new); 181 pass in total.
- **Validation:** report in `experiments/dashboard/validation_report.md`; screenshots in `deliverables/screenshots/v7/`.

## Homepage Polish and Authentication Entry Points — 2026-10-23

### Prompt
> ADMITCOMPASS — HOMEPAGE POLISH AND AUTHENTICATION ENTRY POINTS. (Attached: a screenshot of the current site and a redesigned visual concept as the target direction, not a source of facts.)
>
> 1. **Navigation:** a proper top header with logo, four centered links, and Sign In (outlined) / Sign Up (solid); an accessible mobile menu; anchors offset for a sticky header.
> 2. **Hero:** keep the headline; navy-to-indigo background; two columns with copy, CTAs and a trust strip, plus a larger interactive preview built from real saved-demo data; no fabricated facts.
> 3. **Sections:** dark hero to light sections; a four-step How It Works; a six-program evidence-backed showcase; an international section; a closing CTA and footer.
> 4. **Sign In / Sign Up:** inspect for a real auth backend. If there is none, don't fake accounts or store passwords; label it "Coming soon" and offer "Continue without account".
> 5. **Visual system:** fonts, palette, radii, restrained shadows.
> 6. **QA:** 1440/768/375; no overlap or horizontal scroll; links, CTAs, preview, dialogs, focus and Escape; all tests; no paid calls; no push; screenshots. Stop for review.

### Output summary
- **Changed files:** `frontend/index.html` (header, footer), `frontend/app.js` (renderHome, productPreview, openAuth, route), new `frontend/styles-home.css`, and `backend/app/tools/dashboard.py` (figure vs statement), plus one new test.
- **Auth:** no backend found, so the dialogs say "Coming soon" and have no inputs.
- **Results:** 182 tests pass. Screenshots are in `deliverables/screenshots/v8/`.

## Step 11: Implement Real User Accounts — 2026-10-23

### Prompt
> STEP 11 — ADMITCOMPASS: IMPLEMENT REAL USER ACCOUNTS. The user rejects the Coming Soon dialogs and wants working authentication.
> - **Accounts:** email/password sign-up (name, email, password, confirmation; validation; normalized unique email; Argon2id or another appropriate hash). Sign-in with rate limiting and server-side sessions (random token, only its hash stored, HttpOnly SameSite=Lax cookie, Secure on HTTPS, expiry, rotation). Sign-out. `/api/auth/me`; the user's name and Sign Out in the nav.
> - **Saved work:** account-linked saved programs, profile and completed tasks, with strict authorization. Guest data stays local; opt-in import with validation and duplicate handling.
> - **Frontend:** polished forms with loading, success and error states, show/hide password, accessibility and mobile support.
> - **Security:** CSRF, no credentialed CORS, parameterized SQL, no secrets in logs; document deployment, HTTPS, SQLite and the lack of password reset; don't call it production-ready.
> - **Testing:** cover all of the above plus regression tests, on desktop and mobile.
> - **Scope:** no homepage redesign, payments, social login, email verification, paid calls or push. Stop for review.

### Output summary
- **Backend:** `backend/app/auth/` (security, store, routes) and `scripts/init_db.py`.
- **Frontend:** real forms, header account state, account-backed saved programs, progress and profile, and an import dialog.
- **Docs:** `docs/accounts.md`.
- **Tests:** 16 new auth tests; 198 pass in total.
- **Screenshots:** `deliverables/screenshots/v9/`.

## Step 12: Build a Real Interactive AI Copilot — 2026-10-23

### Prompt
> STEP 12 — ADMITCOMPASS: BUILD A REAL INTERACTIVE AI COPILOT.
> - **A — chat:** an Ask AI launcher; a desktop panel and mobile sheet; session history, composer, loading, errors and suggested questions; multi-turn follow-ups with bounded context; clickable suggestions; New conversation; nothing fake or scripted.
> - **B — backend:** reuse FastAPI and Portkey gpt-6-luna; a dedicated bounded endpoint, not the 4-agent pipeline; deterministic retrieval over evidence and source ids; minimal context; a structured answer with citations, uncertainties and usage; no fabricated sources; general guidance kept distinct from sourced claims.
> - **C — context:** explicit program, comparison and section scope. Example questions: why MIT for this profile, Yale vs Booth, verified STEM, visa sponsorship, next steps. Explain gaps; never odds, guarantees or sponsorship claims.
> - **D — safety:** treat input as untrusted, defend against injection, handle PII, rate and session limits, input and output budgets, key and API failure handling, never expose the key, no permanent chat storage, no paid calls without approval.
> - **E — design:** premium AI feel in the existing style, clickable citations, clear uncertainty, accessibility, mobile and reduced motion.
> - **F — testing:** UI states, suggestions, follow-ups, retrieval and grounding, unknowns, injection and limits, all mocked; regression tests.
>
> Deliverables: working chat, sample conversations (mocked or labeled), grounding and safety tests, a token and latency budget, screenshots, files changed and limitations. Stop for review.

### Output summary
- **Backend:** `backend/app/copilot/` (retrieval, service, routes).
- **Frontend:** the copilot in `frontend/app.js` and `frontend/styles-copilot.css`.
- **Tests:** `tests/test_copilot.py` (22, mocked); 220 pass in total.
- **Samples and budget:** `scripts/copilot_samples.py` writes `experiments/copilot/` (mock samples and token budget).
- **Screenshots:** `deliverables/screenshots/v10/` (mock mode).
- **Live calls:** none were made.

## Step 14: MBA Research Engine and Data Completeness — 2026-10-23

### Prompt
> STEP 14 — ADMITCOMPASS: MBA RESEARCH ENGINE AND DATA COMPLETENESS.
> - **Problem:** too many Unknown, Not published, Partially verified and Not enough comparable data labels.
> - **Authorized sources:** official university pages, U.S. News, Poets&Quants and Clear Admit. Respect paywalls, robots, rate limits and terms; don't reproduce substantial copyrighted tables.
> - **Source priority:** official sources for program facts; secondary sources for estimates and context; never overwrite official values; ranking is not career fit.
> - **Targets:** name and format, location and duration, tuition, fees, cost of attendance and its period, STEM tracks, test policy, class profile, outcomes with definitions, officially documented scholarships, deadlines.
> - **Evidence model:** provenance, period basis, official vs secondary, published vs estimate, retrieval date, status, comparability notes.
> - **MIT example:** official $91,892 tuition and fees vs P&Q's $144,325 estimated annual cost; store both with distinct labels.
> - **Validation:** independently retrieve and validate every fact; don't use the prompt as evidence.
> - **UX:** precise statuses, separate tuition and estimates, years labeled, sources one click away, gaps in expandable details, nothing invented, no coverage ratios.
> - **Implementation:** audit, the six originals first, then the other 24; a deterministic pipeline; preserve conflicts; update Explore, compare, dashboard and copilot; keep safety.
> - **Tests:** sources and identity, period comparability, official vs estimate, conflicts and older years, unknown and blocked fields, the copilot not calling estimates official.
> - **Constraints:** 3-hour timebox; report; stop for review.

### Output summary
- **Research:** 3 research subagents (official pages only) plus transcribed P&Q and Clear Admit figures, all re-validated by `scripts/build_supplementary.py` against live raw pages. 176 facts verified; 28 gaps recorded with reasons.
- **Code:**
  - `backend/app/schemas/supplementary.py` and `backend/app/tools/supplementary.py`;
  - catalog, detail, dashboard and copilot integration;
  - UI cost lines, research blocks and compare rows;
  - `tests/test_research.py` (16 tests); 236 pass in total.
- **Report and screenshots:** `experiments/research/research_report.md`; screenshots in `deliverables/screenshots/v11/`.

## Final sprint (Tasks 1–6) — 2026-10-23/24

### Prompt (summary of the owner's message)
> Continue AdmitCompass (due Oct 26, 6 PM). Feature and design freeze; tasks in order; after each one, run the tests and update `docs/rubric_tracker.md`. Never invent data; stop if a download is needed. (Later: "you have permission to proceed to the other tasks till we finish all the tasks.")
> 1. **Employer sponsorship evidence:** DOL OFLC H-1B LCA data (most recent complete FY), with the real columns inspected; `build_sponsorship.py`; certified cases only; consulting, product management and finance/strategy occupations; Boston, Seattle, Houston, New York and the SF Bay Area; aggregated `lca_filtered.csv` plus provenance; a reviewed alias table; a join to verified employer lists; a `get_sponsorship_evidence` tool; guarantee blocking; the exact note shown; tests; 2 safety scenarios.
> 2. **Demo fixtures:** the Ghana and U.S. fixtures; detailed-only shortlist; visibly different results; the international layer only for Ghana.
> 3. **Fresh live runs:** with the Portkey cache force-refreshed; tokenomics per agent and per run; prices in `.env.example` with source notes; costs at 1, 100 and 10,000 users; a live UI run with screenshots.
> 4. **Run anywhere:** `.env.example`; Python 3.10/3.11; fresh-clone scripts (`.sh` and Windows); grader README; history moved to `docs/CHANGELOG.md`.
> 5. **Trim scope:** accounts behind `AC_ENABLE_ACCOUNTS` (off by default); the copilot kept only if it works live, with usage logged and counted against the budget.
> 6. **Report evidence prep:** Mermaid agent diagram plus PNG/SVG; competitor prompts, scoring template and placeholder table; evidence index.

### Output summary
Done. The details for each task are in `docs/rubric_tracker.md` under "Final-sprint task log". Tests: 266 passed, 1 skipped; safety 26/26. Paid calls: 2 four-agent runs, 1 web-UI run and 2 short copilot checks (9 copilot questions).
