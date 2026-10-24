# Tokenomics analysis (real runs)

Source data: provider-reported usage (`response.usage`) from Portkey for `gpt-6-luna`, saved in `experiments/agent_runs/*/trace.json`. Regenerate with `.venv\Scripts\python experiments\tokenomics\analyze_runs.py` (writes `tokenomics_analysis.json`).

## Price: unknown
No documented `gpt-6-luna` price was found. I checked the course site home page, the instructions page, the project requirements page, and the provider configuration on 2026-10-23. **All dollar figures below are hypothetical scenarios**, not real costs.

## Complete run `20261023T180104Z` (fictional tech-PM applicant, reasoning effort low)

| Agent | Requests | Input tokens | Cached input | Output tokens | Reasoning (inside output) | Model time |
|---|---|---|---|---|---|---|
| Pathway Matcher | 4 | 16,678 | 4,735 | 3,983 | 176 | 4.0 s* |
| Evidence Analyst | 9 | 67,608 | 52,935 | 7,881 | 1,059 | 24.3 s* |
| Strategy Planner | 2 | 11,983 | 6,930 | 2,458 | 0 | 16.8 s |
| Skeptic | 1 | 8,772 | 0 | 614 | 405 | 5.7 s |
| **Total** | **16** | **105,041** | **64,600 (61.5%)** | **14,936** | **1,640** | **50.7 s (end-to-end 50.7 s)** |

\* Includes requests that appear to have been replayed from a cache (see below), so this latency is lower than a fresh run's would be.

Tool calls: 24, of which 6 were identical repeats served from the per-run tool cache (deterministic, no model cost).

## Where the tokens went (overhead)
| Overhead | Requests | Input tokens | Output tokens | Share of run input |
|---|---|---|---|---|
| Pathway Matcher schema retry (verified claim without evidence ids) | 1 | 7,124 | 1,974 | 6.8% |
| Evidence Analyst grounding retry (re-ran the whole tool loop) | 4 | 29,980 | 3,592 | 28.5% |
| **Retry overhead total** | **5 of 16** | **37,104** | **5,566** | **35.3%** |

Repeated tool calls: the grounding retry asked again for all 4 `get_program_facts` calls and both `compare_employment_metrics` calls (seq 34–41). The per-run tool cache served them, but each extra *model* round still re-sent the growing conversation.

## Cache effects, and why this run is not a clean fresh-generation benchmark
- **Provider prompt caching** (the `cached_input_tokens` field): 61.5% of input tokens were reported as cached. The prefix shared across an agent's tool rounds is re-sent each round, which is why the Evidence Analyst reports 52,935 cached tokens.
- **Probable response replay:** requests 1–9 of this run (the whole Pathway Matcher and the Evidence Analyst's first pass) reported token usage **byte-identical** to the earlier run `20261023T175556Z`, 8 of them in under 1 s. That's consistent with Portkey answering identical requests from a response cache. It is not confirmed, and it's unknown whether replays are billed.
- **Consequence:** only requests 10–16 are certainly fresh generations (50,735 input tokens, 31,357 of them cached, plus 6,664 output). A clean benchmark needs an input that has never been sent before (e.g. the second fictional applicant), or caching disabled.

## Hypothetical cost scenarios (NOT real prices)
Formula: `cost_per_run = (input − cached) × P_in + cached × P_cached + output × P_out`, using the complete run's reported tokens (105,041 input / 64,600 cached / 14,936 output). Assumes 3 runs per user per month.

| Scenario (USD per 1M tokens: in / cached / out) | Per run | Per user / month | 100 users / month | 10,000 users / month |
|---|---|---|---|---|
| H1 low: 0.50 / 0.05 / 2.00 | $0.053 | $0.16 | $16.00 | $1,599.68 |
| H2 mid: 2.00 / 0.20 / 8.00 | $0.213 | $0.64 | $63.99 | $6,398.70 |
| H3 high: 5.00 / 0.50 / 20.00 | $0.533 | $1.60 | $159.97 | $15,996.75 |

Applying the optimized orchestrator's estimated reduction (−29.9% input, see `optimization_comparison.md`) would lower these roughly proportionally. That is an estimate from a mock replay, not a measured bill.

## Limitations
- One complete real run; its first 9 requests were probably replayed, so its latency and possibly its billing aren't representative.
- Reasoning tokens are counted inside output tokens, as the provider reports them.
- Tool calls cost no model tokens themselves, but every tool round adds a model request that re-sends the conversation.
