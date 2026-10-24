# Tokenomics — clean live runs (Task 3)

Runs: `20261024T020115Z_fixture-audit-consulting-ghana` (completed), `20261024T020259Z_fixture-domestic-tech-us` (completed_with_violations), `20261024T024740Z_fixture-audit-consulting-ghana_webui` (stopped_budget), `20261024T024921Z_fixture-domestic-tech-us_webui` (completed_with_violations), `20261024T031733Z_fixture-audit-consulting-ghana` (stopped_budget), `20261024T032006Z_fixture-audit-consulting-ghana` (completed_with_violations). Portkey's cache was force-refreshed on every request, so these tokens are fresh generations.

"Cached input" is the model provider's own prompt caching inside a run (an agent's repeated system prompt and history on its follow-up tool calls), reported by the API's usage field. It is not a replay of an earlier response.

## Tokens per run

| Run | Requests | Input | Cached input | Output | (reasoning) | Tool calls | Wall s |
|---|---:|---:|---:|---:|---:|---:|---:|
| 20261024T020115Z_fixture-audit-consulting-ghana | 13 | 48,478 | 25,832 | 7,599 | 947 | 8 | 96.768 |
| 20261024T020259Z_fixture-domestic-tech-us | 11 | 75,759 | 39,251 | 11,186 | 705 | 26 | 99.933 |
| 20261024T024740Z_fixture-audit-consulting-ghana_webui | 20 | 127,853 | 66,773 | 16,894 | 1,002 | 31 | 110.668 |
| 20261024T024921Z_fixture-domestic-tech-us_webui | 13 | 82,284 | 45,034 | 10,666 | 528 | 17 | 69.35 |
| 20261024T031733Z_fixture-audit-consulting-ghana | 20 | 158,952 | 77,243 | 21,301 | 929 | 31 | 126.812 |
| 20261024T032006Z_fixture-audit-consulting-ghana | 9 | 54,756 | 26,621 | 8,779 | 696 | 17 | 53.778 |

## Tokens per agent

**20261024T020115Z_fixture-audit-consulting-ghana**

| Agent | Requests | Input | Cached input | Output | (reasoning) | Model s |
|---|---:|---:|---:|---:|---:|---:|
| pathway_matcher | 5 | 12,972 | 9,321 | 1,380 | 282 | 18.49 |
| evidence_analyst | 5 | 21,809 | 16,511 | 1,340 | 168 | 45.26 |
| strategy_planner | 2 | 8,432 | 0 | 4,531 | 218 | 25.59 |
| skeptic | 1 | 5,265 | 0 | 348 | 279 | 7.32 |

**20261024T020259Z_fixture-domestic-tech-us**

| Agent | Requests | Input | Cached input | Output | (reasoning) | Model s |
|---|---:|---:|---:|---:|---:|---:|
| pathway_matcher | 4 | 16,340 | 11,231 | 2,002 | 144 | 17.61 |
| evidence_analyst | 3 | 30,384 | 17,961 | 3,577 | 52 | 20.7 |
| strategy_planner | 3 | 20,294 | 8,736 | 4,721 | 93 | 54.06 |
| skeptic | 1 | 8,741 | 1,323 | 886 | 416 | 7.08 |

**20261024T024740Z_fixture-audit-consulting-ghana_webui**

| Agent | Requests | Input | Cached input | Output | (reasoning) | Model s |
|---|---:|---:|---:|---:|---:|---:|
| pathway_matcher | 6 | 20,738 | 9,911 | 3,808 | 100 | 29.2 |
| evidence_analyst | 10 | 87,954 | 51,756 | 9,498 | 437 | 55.31 |
| strategy_planner | 3 | 16,200 | 6,839 | 2,709 | 116 | 18.5 |
| skeptic | 1 | 8,583 | 0 | 914 | 349 | 7.32 |

**20261024T024921Z_fixture-domestic-tech-us_webui**

| Agent | Requests | Input | Cached input | Output | (reasoning) | Model s |
|---|---:|---:|---:|---:|---:|---:|
| pathway_matcher | 4 | 12,644 | 7,954 | 1,693 | 0 | 15.62 |
| evidence_analyst | 6 | 50,726 | 29,050 | 6,230 | 432 | 35.02 |
| strategy_planner | 2 | 11,032 | 6,707 | 2,184 | 96 | 13.66 |
| skeptic | 1 | 7,882 | 1,323 | 559 | 0 | 4.9 |

**20261024T031733Z_fixture-audit-consulting-ghana**

| Agent | Requests | Input | Cached input | Output | (reasoning) | Model s |
|---|---:|---:|---:|---:|---:|---:|
| pathway_matcher | 6 | 21,713 | 11,930 | 3,713 | 269 | 24.1 |
| evidence_analyst | 10 | 107,922 | 49,815 | 13,704 | 437 | 71.54 |
| strategy_planner | 3 | 19,643 | 14,175 | 2,996 | 59 | 23.65 |
| skeptic | 1 | 9,674 | 1,323 | 888 | 164 | 7.09 |

**20261024T032006Z_fixture-audit-consulting-ghana**

| Agent | Requests | Input | Cached input | Output | (reasoning) | Model s |
|---|---:|---:|---:|---:|---:|---:|
| pathway_matcher | 3 | 9,946 | 5,494 | 1,777 | 212 | 11.85 |
| evidence_analyst | 3 | 23,889 | 12,572 | 3,616 | 0 | 19.56 |
| strategy_planner | 2 | 12,169 | 7,232 | 2,637 | 107 | 15.38 |
| skeptic | 1 | 8,752 | 1,323 | 749 | 377 | 6.83 |

## Cost

Price: UNKNOWN — no documented gpt-6-luna price was found; all dollar figures are HYPOTHETICAL scenarios.

Formula: `cost_per_run = (input - cached) * P_in + cached * P_cached + output * P_out`. Assumption: 3 runs per user per month.

| Price set | $/1M in · cached · out | Per run | Per user / month | 100 users / month | 10,000 users / month |
|---|---|---:|---:|---:|---:|
| H1 low (hypothetical) | 0.5 · 0.05 · 2.0 | $0.05009 | $0.1503 | $15.03 | $1,502.76 |
| H2 mid (hypothetical) | 2.0 · 0.2 · 8.0 | $0.20037 | $0.6011 | $60.11 | $6,011.03 |
| H3 high (hypothetical) | 5.0 · 0.5 · 20.0 | $0.50092 | $1.5028 | $150.28 | $15,027.58 |

## Request-cap change: 20 → 25 (2026-10-24)

- **Why:** two Ghana runs stopped at 20/20 requests after a Skeptic-requested revision (`20261024T024740Z_fixture-audit-consulting-ghana_webui`, `20261024T031733Z_fixture-audit-consulting-ghana`). They are kept as evidence that the cap works. The cap was raised to 25 (`ADMITCOMPASS_MAX_REQUESTS_PER_RUN`). The 200,000-token, 40-tool-call and 300-second caps are unchanged, so the **worst-case cost per run is still bounded by the 200k-token cap**.
- **Measured average per request** across these 6 runs: 6,373 input (3,265 cached) and 889 output tokens.
- **Most a run can now spend beyond the old cap:** 5 more requests, about 31,865 input and 4,443 output tokens:

| Price set | Extra cost per run if all 5 extra requests are used |
|---|---:|
| H1 low (hypothetical) | $0.0175 |
| H2 mid (hypothetical) | $0.0699 |
| H3 high (hypothetical) | $0.1747 |

- **Typical runs are unaffected:** completed runs used 9–13 requests. The re-run after the change finished in 9 requests without a revision, so the higher cap only matters when the Skeptic requests a revision on a larger shortlist.
