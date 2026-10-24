# Malfunction found and fixed: sponsorship status overridden by a stale grounding rule (2026-10-24)

**Category:** agent malfunction caught by our own deterministic checks. Here the *check itself* was wrong after a data change.

## What happened
- **Run:** `experiments/agent_runs/20261024T020259Z_fixture-domestic-tech-us/`. It is kept **unedited** as evidence.
- **The new tool worked as intended.** Task 1 had just added the `get_sponsorship_evidence` tool (historical U.S. DOL H-1B filings by employers that a school's official report says hired its graduates). In this run the Evidence Analyst used it and correctly reported `sponsorship_status = "employer_specific_evidence"` for Yale, Booth and Duke.
- **The rule was stale.** The deterministic grounding rule `expected_sponsorship()` (`backend/app/agents/grounding.py`) still said: *employer-specific evidence only if the school-level `sponsorship` fact is verified.* No school publishes such a fact, so the rule "corrected" all three correct answers to `unknown`, logging three `sponsorship_status_mismatch` violations. The run status became `completed_with_violations`.
- **Impact:** the saved report under-stated the available evidence. It said "unknown" where historical employer filings exist. It never over-stated sponsorship, so the failure was in the safe direction, but it was still wrong.

## The fix
`expected_sponsorship()` now returns `"employer_specific_evidence"` when **either** the school-level fact is verified **or** `get_sponsorship_evidence(program_id)` finds at least one listed employer with historical filings. It still never means a promise: the separate `sponsorship_guarantee` rule blocks any guarantee wording, and the UI shows the mandatory note.

## Tests that now cover it
- `tests/test_agents.py::test_sponsorship_and_affordability_corrected_to_store` checks both directions:
  - **Yale:** has a verified employer list with filings, so the model's `unknown` is corrected to `employer_specific_evidence`.
  - **Rice:** has no employer list, so a model's `employer_specific_evidence` is corrected to `unknown`. (MIT was the example until its list was extracted on 2026-10-24.)
- `tests/test_safety.py` scenario **S05** (fabricated sponsorship) now uses Rice. A fabricated claim citing unrelated (test-policy) evidence is dropped, and the status stays `unknown`.
- `tests/test_sponsorship.py`, `tests/test_demo_fixtures.py`: the join and scoping that the rule depends on.

## Confirmation with a fresh live run
- **Run:** `experiments/agent_runs/20261024T024921Z_fixture-domestic-tech-us_webui/` (web UI, same fixture, current code).
- **Statuses:** Booth and Duke `employer_specific_evidence`, MIT `unknown`. There are **no** `sponsorship_status_mismatch` violations.
- **The single remaining violation** is a legitimate catch: a STEM claim cited the wrong fact and was dropped.
