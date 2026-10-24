# User evaluation protocol (2–3 testers, about 30 minutes each)

**Status: protocol ready. No sessions run yet. No results recorded.** Results go in `experiments/user_testing/` only after real sessions.

## Who
2–3 people who are prospective or recent graduate-school applicants, ideally international (e.g. classmates or friends considering an MBA). Not the author. Verbal consent; no names, emails, or personal identifiers recorded. Use tester codes T1, T2, T3.

## Task (same for every tester)
> "You are an Indian software engineer, 5 years' experience, aiming for product management at a US tech company after an MBA. Your budget is $135,000 per academic year, and you will need US work authorization after graduating. From Yale SOM, HBS, MIT Sloan, Chicago Booth, Duke Fuqua and Rice Jones, choose a shortlist of programs and answer the five questions below."

This is the fictional tech-PM applicant, so testers don't share personal data and the saved real analysis can be used (no paid run needed).

**Questions to answer (the success criteria):**
1. Which programs fit the budget, based on total cost of attendance, not tuition alone?
2. Which programs are officially STEM-designated, and what is your source?
3. Is there evidence that employers of these programs' graduates sponsor work visas?
4. Can you directly compare these programs' employment rates? Why or why not?
5. What should you do in the next 2 weeks?

**Answer key** (from the evidence store; the grader uses it, the tester doesn't see it):
1. Booth $132,449, Fuqua $118,974 and Yale $128,976 are within budget for 2026-27; HBS $130,318 is also within budget (and was excluded by the agents for other reasons); MIT and Rice have no verified total cost, so they're unknown.
2. All 6 are STEM-designated per official pages (scope differs: HBS from the Class of 2025, Yale from the Class of 2026).
3. No employer-specific sponsorship evidence on any official page → unknown.
4. No: the definitions and denominators differ.
5. Open-ended; credit concrete, time-bound actions.

## Design: within-subject, counterbalanced
| Tester | First | Second |
|---|---|---|
| T1 | Baseline | AdmitCompass |
| T2 | AdmitCompass | Baseline |
| T3 | Baseline | AdmitCompass |

- **Baseline:** ordinary ChatGPT (whatever the tester normally uses) plus any web search. Max 20 minutes.
- **AdmitCompass:** `http://127.0.0.1:8000` → Saved demo (`#/results/demo`). Max 15 minutes.
- Learning effect: the second condition benefits from the first. Counterbalancing reduces this but doesn't remove it with n = 3. Report it as a limitation.

## Measurements
- **Time to completion** (stopwatch, minutes:seconds) per condition.
- **Accuracy:** each of Q1–Q4 scored 0/1 against the answer key; Q5 scored 0–2.
- **Ratings** (1–5 scale) after each condition: usefulness, trust in the answer, clarity about what is unknown.
- **Specific probes** (after the AdmitCompass condition):
  - "Did you understand why sponsorship is shown as unknown?" (yes / partly / no + quote)
  - "Did you open any source? Did the evidence labels (verified / inference / unknown) change how much you trusted a statement?"
  - "Was anything confusing or missing?"
- **Quote:** ask for one sentence the author may quote anonymously.

## Feedback form (copy per tester and condition)
```
Tester code: T_   Condition: Baseline / AdmitCompass   Order: 1st / 2nd   Date:
Start time: ____   End time: ____   Minutes: ____
Q1 budget fit: ______________________ score 0/1
Q2 STEM + source: ___________________ score 0/1
Q3 sponsorship evidence: ____________ score 0/1
Q4 comparable employment rates?: ____ score 0/1
Q5 next 2 weeks: ____________________ score 0/1/2
Usefulness (1-5): __   Trust (1-5): __   Clarity about unknowns (1-5): __
Sponsorship-unknown understood? yes / partly / no   Comment:
Opened a source? yes / no   Labels affected trust? yes / no   Comment:
Confusing or missing:
Quotable sentence (with permission):
```

## Reporting rules
- Report raw numbers per tester and the median. With n ≤ 3, make no statistical claims.
- Record real results only. If fewer than 2 sessions happen, say so and report what exists (e.g. one session, or the author's own timed run clearly labelled as such).
- Save to `experiments/user_testing/sessions.csv` (template provided) and quotes to `experiments/user_testing/quotes.md`.
