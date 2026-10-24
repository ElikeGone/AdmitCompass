# Optimization comparison: baseline vs optimized orchestrator

Script: `experiments/tokenomics/optimization_experiment.py` → `optimization_comparison.json`. Requires the experiment-only tokenizer (`pip install -r experiments/requirements-experiments.txt`).

## What changed (Step 7)
1. **Repair-mode grounding retry.** When an agent's answer has grounding errors, the old code re-ran the agent from scratch, including its whole tool loop. The new code sends **one** request with tools disabled, containing the previous answer, the exact errors, and the evidence the agent already retrieved. Grounding then runs again on the repaired answer, so the checks are unchanged.
2. **Downgrade instead of retry.** A claim labelled `verified_fact` that cites no evidence is relabelled `inference` in code, instead of triggering a schema retry. This weakens the claim, never the verification.

The baseline (`Orchestrator(optimized=False)`) is preserved for comparison.

## Method
- **Same deterministic mock model for both modes**, built from the real run `20261023T180104Z`:
  - the real tool-call rounds of each agent, from `trace.json`;
  - the real validated agent outputs, from `agent_outputs.json`;
  - the two failure types from real runs, re-injected identically in both modes (Pathway claim without evidence ids; Evidence Analyst claim with an unsupported number).
- Same fictional applicant profile and same evidence store.
- **Measured:** serialized request size in characters (messages + tool schemas), and requests, tool calls, validations and grounding results.
- **Estimated:** input tokens via `tiktoken` `o200k_base`. `gpt-6-luna`'s tokenizer is not published, so these are estimates. **None of this is provider-reported usage or Portkey billing.**

## Results

| Metric | Baseline | Optimized | Change |
|---|---|---|---|
| Model requests | 17 | 12 | **−5 (−29.4%)** |
| Serialized request characters | 507,762 | 358,047 | −29.5% |
| Estimated input tokens (o200k) | 126,939 | 88,935 | **−38,004 (−29.9%)** |
| Pathway Matcher requests / est. tokens | 4 / 19,259 | 3 / 11,173 | −1 / −42% |
| Evidence Analyst requests / est. tokens | 10 / 85,347 | 6 / 55,392 | −4 / −35% |
| Strategy Planner requests / est. tokens | 2 / 13,047 | 2 / 13,047 | 0 |
| Skeptic requests / est. tokens | 1 / 9,286 | 1 / 9,323 | ≈0 |
| Tool calls executed (excl. cache repeats) | 18 | 18 | 0 |
| Tool calls served from run cache | 7 | 0 | −7 |
| Validation failures | 1 | 0 | −1 |
| Grounding retries | 1 (full re-run: 5 requests) | 1 (repair: 1 request) | same count, 4 fewer requests |
| Final status | completed | completed | same |

Sanity check: the baseline mock reproduces the real run's shape (17 vs 16 real requests; 126,939 estimated vs 105,041 provider-reported input tokens, different tokenizers).

## Quality and grounding preserved?
Compared field by field (`quality_identical` in the JSON):

| Check | Identical? |
|---|---|
| Recommended programs (MIT Sloan, Booth, Fuqua, Yale SOM) | ✅ |
| Analyst claims count, verified-claim count, evidence ids cited | ✅ |
| Final claims failing a re-run of grounding | ✅ (0 in both) |
| Grounding violations recorded | ✅ |
| Strategy weeks, Skeptic findings | ✅ |
| Pathway Matcher claim labels | ❌ **differs, as expected:** optimized keeps the evidence-less claim as `inference`, while baseline regenerated without it. This claim isn't shown in program recommendations. |

## Limitations
- Mock replay: the real model might answer a repair prompt differently from a full re-run. A real fresh run would be needed to confirm the saving on provider-reported tokens (see the proposed experiment in `docs/evidence_index.md`).
- Token counts are estimates; requests and characters are exact for the mock.
