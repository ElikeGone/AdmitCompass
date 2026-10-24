# Tokenomics — clean live runs (Task 3)

Runs: `20261024T020115Z_fixture-audit-consulting-ghana` (completed), `20261024T020259Z_fixture-domestic-tech-us` (completed_with_violations), `20261024T024740Z_fixture-audit-consulting-ghana_webui` (stopped_budget), `20261024T024921Z_fixture-domestic-tech-us_webui` (completed_with_violations). Portkey's cache was force-refreshed on every request, so these tokens are fresh generations.

"Cached input" is the model provider's own prompt caching inside a run (an agent's repeated system prompt and history on its follow-up tool calls), reported by the API's usage field. It is not a replay of an earlier response.

## Tokens per run

| Run | Requests | Input | Cached input | Output | (reasoning) | Tool calls | Wall s |
|---|---:|---:|---:|---:|---:|---:|---:|
| 20261024T020115Z_fixture-audit-consulting-ghana | 13 | 48,478 | 25,832 | 7,599 | 947 | 8 | 96.768 |
| 20261024T020259Z_fixture-domestic-tech-us | 11 | 75,759 | 39,251 | 11,186 | 705 | 26 | 99.933 |
| 20261024T024740Z_fixture-audit-consulting-ghana_webui | 20 | 127,853 | 66,773 | 16,894 | 1,002 | 31 | 110.668 |
| 20261024T024921Z_fixture-domestic-tech-us_webui | 13 | 82,284 | 45,034 | 10,666 | 528 | 17 | 69.35 |

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

## Cost

Price: UNKNOWN — no documented gpt-6-luna price was found; all dollar figures are HYPOTHETICAL scenarios.

Formula: `cost_per_run = (input - cached) * P_in + cached * P_cached + output * P_out`. Assumption: 3 runs per user per month.

| Price set | $/1M in · cached · out | Per run | Per user / month | 100 users / month | 10,000 users / month |
|---|---|---:|---:|---:|---:|
| H1 low (hypothetical) | 0.5 · 0.05 · 2.0 | $0.04507 | $0.1352 | $13.52 | $1,352.07 |
| H2 mid (hypothetical) | 2.0 · 0.2 · 8.0 | $0.18028 | $0.5408 | $54.08 | $5,408.3 |
| H3 high (hypothetical) | 5.0 · 0.5 · 20.0 | $0.45069 | $1.3521 | $135.21 | $13,520.74 |
