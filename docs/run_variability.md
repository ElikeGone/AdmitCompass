# Same profile, different shortlists: run-to-run variability (observed 2026-10-24)

The Pathway Matcher is a language model. Given the same profile, the same 5 "detailed" programs and the same tools, it can choose a different shortlist on different runs. Everything that follows the choice is deterministic code and always gives the same answer for a given program and profile: costs and the budget gap, STEM status, sponsorship status, the grounding checks and the H-1B evidence.

| Fixture | Run | Where | Budget | Shortlist | Status |
|---|---|---|---|---|---|
| Ghana (audit → consulting, Boston) | `20261024T020115Z_fixture-audit-consulting-ghana` | command line | $120,000/yr | MIT Sloan | completed |
| Ghana | in-memory web run `45b21386ed10` (screenshots `final/task3_*`; not saved to disk) | web UI | $120,000/yr | MIT Sloan, Duke Fuqua | completed |
| Ghana | `20261024T024740Z_fixture-audit-consulting-ghana_webui` | web UI | **$140,000/yr** (raised) | MIT Sloan, Yale SOM, Duke Fuqua | stopped_budget (20/20 requests, during a Skeptic-requested revision) |
| U.S. (engineering → PM, Seattle) | `20261024T020259Z_fixture-domestic-tech-us` | command line | $150,000/yr | Yale SOM, Chicago Booth, Duke Fuqua | completed_with_violations (stale-rule malfunction, see `experiments/safety/malfunction_sponsorship_status.md`) |
| U.S. | `20261024T024921Z_fixture-domestic-tech-us_webui` | web UI | $150,000/yr | MIT Sloan, Chicago Booth, Duke Fuqua | completed_with_violations (1 legitimate STEM-citation drop) |

## Why it happens
- **Model judgment.** Shortlisting weighs career fit, location and budget. The prompts ask for career-first reasoning but don't fix a scoring formula, by design: AdmitCompass doesn't produce match scores.
- **Example:** in the $140k Ghana run, Booth was within budget ($132,449) but was excluded *by the model*. Its stated reason: "verified location, Chicago, is less aligned with the stated Boston preference". Tuck was excluded for the same reason (Hanover, NH). **No code rule removed either one.** The only code-level filter on the demo shortlist is "detailed evidence programs only".
- **Searches differ too.** In one run the matcher searched with `states=MA` (interpreting "Boston"); in another it searched with no state filter. The trace records each call.

## What stays stable
- Deterministic facts for each program never vary: cost of attendance, the budget gap, STEM status, the employer H-1B filings and the required note.
- The Skeptic reviews every run, and grounding removes unsupported claims in every run.

## Implication for users and the report
A shortlist is a *starting set to research*, not a ranking. Re-running can surface other plausible programs. The report should present one run as an example and say that shortlists can vary between runs.
