# False positive found and fixed: a correct warning flagged as a "guarantee" (2026-10-24)

## What happened
- **Run:** `experiments/agent_runs/20261024T032006Z_fixture-audit-consulting-ghana/`, kept unedited.
- **The text:** the Strategy Planner wrote a correct caution in `gaps[4].action`: "…Do not treat historical employer filings as a guarantee…".
- **The bug:** the `guarantee` rule in `risky_language()` (`backend/app/agents/grounding.py`) only looked **40 characters** back for a negation. "Do not treat" was further away, so the warning was flagged.
- **Effect:** the line was flagged, not removed, but the run was labeled `completed_with_violations` for a correct statement.

## While writing the regression test, a second weakness was found
The 40-character look-back could also *suppress* a real guarantee whenever an unrelated negation appeared earlier in the same sentence. For example, "It is not cheap, but it guarantees a job" was not flagged.

## The fix
- **Negations must be in the same clause.** The look-back now stops at `. ; ! ?` and at `but`, `however` and `yet`.
- **Negated "as a guarantee" framing is recognized.** If the same sentence says *do not / never / not … as / is / imply (a) guarantee*, the word "guarantee" is treated as negated (`NEGATED_AS`).

## Tests
`tests/test_sponsorship.py::test_negated_guarantee_framing_is_not_flagged` checks four cases:

| Text | Result |
|---|---|
| "Do not treat historical employer filings as a guarantee of sponsorship." | not flagged |
| "Past filings do not imply a guarantee." | not flagged |
| "It is not cheap, but it guarantees a job." | **flagged** |
| "This MBA guarantees you an H-1B." | **flagged** |

The full safety suite still passes 26/26, including S24 (a correct immigration warning isn't flagged) and S25 (a guarantee is blocked).
