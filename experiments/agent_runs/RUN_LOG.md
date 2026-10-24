# Real agent run log (gpt-6-luna via Portkey)

All runs use the fictional fixture `data/fixtures/applicant_tech_pm.json`. Every folder holds `input_profile.json`, `agent_outputs.json`, `trace.json`, `report.json`, and `usage_summary.json`.

| Folder | Endpoint | Result | Model requests | Tokens |
|---|---|---|---|---|
| `20261023T174645Z_fixture-tech-pm-india` | `/v1/chat/completions` | **failed_closed** — HTTP 400: "Function tools with reasoning_effort are not supported for gpt-6-luna-global in /v1/chat/completions" | 0 (rejected) | 0 |
| `20261023T175353Z_fixture-tech-pm-india` | `/v1/responses` | **failed_closed** — HTTP 400: JSON mode needs the word "json" in the input messages (adapter bug; fixed) | 0 (rejected) | 0 |
| `20261023T175556Z_fixture-tech-pm-india` | `/v1/responses`, reasoning effort low | **stopped_budget** — 14/14 request cap hit during the Strategy Planner's first tool round | 14 | 84,358 input (57,724 cached) + 11,697 output (1,235 reasoning) |
| `20261023T180104Z_fixture-tech-pm-india` | `/v1/responses`, reasoning effort low, 20-request budget | **completed_with_violations** — all 4 agents ran; Skeptic requested no revision; 1 flagged (false-positive) language violation | 16 | 105,041 input (64,600 cached) + 14,936 output (1,640 reasoning) |

Separate compatibility check: `experiments/smoke_test/responses_tools_20261023T175249Z.json` — one tool call plus result round-trip succeeded (2 requests, 209 tokens).

## What the budget-stopped run showed
- The Pathway Matcher used both tools (`search_programs`, then 6× `get_program_overview`). Its first answer failed schema validation (verified claims without evidence ids); the retry passed. It shortlisted 4 programs: MIT Sloan, Chicago Booth, Duke Fuqua, Yale SOM.
- The Evidence Analyst used `get_program_facts` ×5 and `compare_employment_metrics` ×2 (an identical repeat). Grounding dropped 3 claims and triggered one retry.
- **Root cause (my bug, now fixed):** those 3 claims correctly restated the applicant's own $135,000 budget, and the number check only allowed numbers from program evidence. Numbers from the applicant profile are now allowed too. Regression test: `test_profile_budget_number_allowed_in_verified_claim`.
- Identical repeat tool calls are now served from a per-run cache (`test_repeated_identical_tool_call_served_from_cache`).
- The budget guard worked as designed: it stopped the run before the 15th request and saved a partial report. Defaults were raised to 20 requests / 200,000 tokens, based on this measurement.
- Cost: unknown. No documented gpt-6-luna price is configured.

## Complete run: `20261023T180104Z_fixture-tech-pm-india` (the run cited in the report)
Status `completed_with_violations`, 16/20 requests, 119,977/200,000 budget tokens, 24/40 tool calls, 50.7 s wall time. Cost unknown (no documented gpt-6-luna price).

| Agent | Requests | Input | Cached input | Output | Reasoning (in output) | Model time |
|---|---|---|---|---|---|---|
| Pathway Matcher | 4 | 16,678 | 4,735 | 3,983 | 176 | 4.0 s |
| Evidence Analyst | 9 | 67,608 | 52,935 | 7,881 | 1,059 | 24.3 s |
| Strategy Planner | 2 | 11,983 | 6,930 | 2,458 | 0 | 16.8 s |
| Skeptic | 1 | 8,772 | 0 | 614 | 405 | 5.7 s |
| **Total** | **16** | **105,041** | **64,600 (61.5%)** | **14,936** | **1,640** | **50.7 s** |

**Sequence:** Pathway Matcher (`search_programs` → 6× `get_program_overview` → answer failed schema: verified claims without evidence ids → retry passed) → Evidence Analyst (5× `get_program_facts`, `compare_employment_metrics` for employment rate and for salary → grounding: 3 unsupported claims → grounding retry, where all 5 tool calls were served from the per-run cache → 1 flagged violation) → Strategy Planner (4× `get_program_facts` → plan) → Skeptic (no tools; 1 medium finding; no revision request).

**Final shortlist:** MIT Sloan (strong; affordability **unknown**, cost of attendance not verified), Chicago Booth (strong; within budget, $132,449 vs $135,000), Duke Fuqua (moderate; within budget, $118,974), Yale SOM (moderate; within budget, $128,976). Excluded: HBS, Rice. Sponsorship is **unknown** for all 4. Employment rate and salary are marked **not comparable** (definitions differ).

**Skeptic finding (medium, Strategy Planner):** the test guidance opened with "all four require GMAT or GRE", which hides that Fuqua also accepts the Executive Assessment. No revision was requested because the finding doesn't change the recommendation.

**Post-run audit** (`verification.json`, produced by `scripts/verify_run.py`, no model calls): 36 evidence ids, all exist and belong to the right program; 19 verified claims, all with evidence; 0 numbers in any recommendation text that are absent from the store or profile; no employment metric presented as comparable; STEM and sponsorship statuses match the store. **ok = true.**

### Caveats (important for the report)
1. **Portkey appears to have replayed cached responses.** *(Corrected in Step 7: originally written as "requests 1–13"; a request-by-request comparison shows requests 1–9.)* Requests 1–9 (all of the Pathway Matcher and the Evidence Analyst's first attempt) returned token counts byte-identical to run `20261023T175556Z`, mostly in ~0.2 s. This looks like Portkey response caching of identical requests, but that is not confirmed, and we don't know whether replayed calls are billed. Requests 10–16 (Evidence Analyst retry, Strategy Planner, Skeptic) are certainly fresh generations. For tokenomics, the reported tokens are what the API returned; later experiments must vary the input or disable caching to measure fresh generations.
2. **Trace gap:** the details of the 3 first-pass Evidence Analyst grounding violations were not logged; only the count was. Fixed after this run (grounding events now include violation details, `test_first_pass_grounding_details_logged`), but this run's details can't be recovered without another paid call.
3. **False-positive flag:** the "guarantee" rule flagged the Analyst's correct caution ("...any implication of guaranteed immigration benefit ... is unsupported"); its negation comes after the word. Action was "flagged" only, and nothing was removed.

### Waste and token-reduction opportunities (verification stays intact)
| Observation | Approx. cost | Option |
|---|---|---|
| Evidence Analyst grounding retry re-ran the whole tool loop (4 requests) | ~30k input tokens | On retry, send only the violations + previous answer with no tool loop (one request), or drop invalid claims without retrying when the rest of the dossier is valid |
| Pathway Matcher schema retry for verified claims missing evidence ids | ~7k input | Downgrade such claims to `inference` in code instead of retrying (this weakens the claim, never the verification) |
| Pathway Matcher spends a round on 6× `get_program_overview` | 1 request, ~2k | Return compact overviews inside `search_programs` |
| Strategy Planner re-fetches test policy/requirements already in the dossiers | 1 request, ~5k | Pass those facts in its payload; keep the tool for anything else |
| Context grows each tool round (Analyst rounds 8–9k each) | most of the 67k | Fewer, batched tool calls; prompt asks for one batched `get_program_facts` round |
| Skeptic got 0 cached tokens | 8.8k uncached | Keep a long identical prefix (shared rules + schema) first in all agents' instructions |

## Task 3 clean runs (2026-10-24, Portkey cache force-refreshed)
| Run | Fixture | Status | Requests | Input / cached / output tokens | Wall s |
|---|---|---|---:|---|---:|
| `20261024T020115Z_fixture-audit-consulting-ghana` | Ghana, audit → consulting (Boston) | completed | 13 | 48,478 / 25,832 / 7,599 | 97 |
| `20261024T020259Z_fixture-domestic-tech-us` | U.S., engineering → product management (Seattle) | completed_with_violations | 11 | 75,759 / 39,251 / 11,186 | 100 |

- **Demo restriction:** both runs used the 5 "detailed" programs only.
- **Shortlists differ:** Ghana got MIT Sloan; the U.S. profile got Yale, Booth and Duke.
- **The U.S. run's 3 violations** were `sponsorship_status_mismatch`. The Evidence Analyst correctly reported employer-specific H-1B evidence from the new tool, but the deterministic rule at that moment still required a school-level sponsorship fact, so it overrode the answer. The rule was fixed right after this run: DOL employer evidence now counts as employer-specific evidence, never as a promise. The saved run is kept unedited.

## Follow-up web-UI runs (2026-10-24, current code, cache force-refreshed; saved with `scripts/save_ui_run.py`)
| Run | Fixture | Status | Requests | Shortlist |
|---|---|---|---:|---|
| `20261024T024740Z_fixture-audit-consulting-ghana_webui` | Ghana, budget raised to $140k/yr | stopped_budget | 20 | MIT Sloan, Yale SOM, Duke Fuqua |
| `20261024T024921Z_fixture-domestic-tech-us_webui` | U.S. | completed_with_violations | 13 | MIT Sloan, Chicago Booth, Duke Fuqua |

- **Ghana:** the full pipeline ran; then the Skeptic requested a Pathway Matcher revision, and the re-run hit the 20-request cap (the overspend defense working). The report keeps the shortlist, strategy and Skeptic output.
- **U.S.:** sponsorship statuses are now correct (Booth and Duke `employer_specific_evidence`, MIT `unknown`). The one violation is a legitimate STEM-citation drop.
- **Shortlist differences between runs:** see `docs/run_variability.md`.
