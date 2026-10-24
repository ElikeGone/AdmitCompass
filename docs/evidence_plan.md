# Evidence Capture Plan

**Rule: never fabricate evidence.** Every number, quote, and screenshot comes from a real run or a real person, with date and raw files saved. If something cannot be captured, the report says so (and accepts the half-points cap) rather than inventing it.

| # | Evidence | Rubric rows | How it's captured | Saved to | Status |
|---|---|---|---|---|---|
| 1 | **Competitor comparison** | Novelty 21, Motivation 8 | Run 2 fixture profiles' questions in ChatGPT (free/default) + note 2–3 other tools (school sites, rankings, consultants). Score each on: sources cited, STEM correctness, sponsorship caveats, actionable plan, cost/time. User runs ChatGPT manually; responses saved verbatim with date. | `experiments/competitor_comparison/` | pending |
| 2 | **One complete real agent trace + screenshots** | Agent design 10, Look+feel 10 | Run a fixture profile; export trace JSON (agent, tool calls, handoffs, Skeptic critiques, revision); screenshot each UI stage | `experiments/traces/`, `deliverables/screenshots/` | pending |
| 3 | **Actual tokens & costs** | Tokenomics 8 | Log `usage.prompt_tokens`, cached tokens (`prompt_tokens_details.cached_tokens`), `completion_tokens` per call from API responses; ≥5 runs; cost = tokens × confirmed `gpt-6-luna` price (source cited); extrapolate per user/month, 100 & 10,000 users with stated assumptions | `experiments/tokenomics/runs.csv` | pending (price unknown) |
| 4 | **Cost-reduction experiment + quality comparison** | Tokenomics 8 | Baseline (full evidence text, no caching-friendly prompts, unlimited output) vs optimized (compact JSON evidence, stable prefixes, output caps, deterministic tools). Same profiles; compare cost and quality (claim-label completeness, unsupported-claim count, rubric score by user) | `experiments/tokenomics/cost_experiment.md` | pending |
| 5 | **Tested safety defense** | Safety 8 | Automated tests: (a) prompt injection in profile field and in an evidence snippet; (b) unsupported "STEM"/"sponsors" claim is caught by validator/Skeptic; (c) cost cap stops a runaway run; (d) admission-probability request refused. Record pass/fail + screenshots | `tests/test_safety.py`, `experiments/safety/` | pending |
| 6 | **Real-user feedback or timed baseline** | Impact 5 | 1–3 real prospective/international applicants (with consent, no PII stored): time to answer a fixed question set manually vs with app, plus a short quote. Fallback: user (author) timed self-test, labeled as such | `experiments/user_testing/` | pending |
| 7 | **Fresh-clone test** | Staff can run it 5 | Clone into new folder, `.env` only one level above, follow README with a timer | `experiments/fresh_clone_test.md` | pending |

Inputs needed from the user: ChatGPT comparison runs, recruiting 1–3 test users, confirmed `gpt-6-luna` pricing.
