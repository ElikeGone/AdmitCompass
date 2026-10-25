# Impact test — protocol, scoring rubric and three-user results

**Status (2026-10-24): three real testers (T1, T2, T3) used AdmitCompass and gave feedback. Their feedback is recorded below as paraphrased recollections, not verbatim quotes. No task-completion, timing or score data was documented.** See "Recorded results — three testers" at the end. The protocol, answer key and scoring rubric below are unchanged; use them, with the blank template, for any future session.

*Original status note (kept for the record): "ready to run. No session run yet. No results recorded." Fill in the "Results" section only after a real session; leave any field you didn't observe blank. Don't invent or estimate results.*

**Purpose:** check whether a real person can use the Sample Analysis to make the decisions AdmitCompass is built for, and how long it takes to find the next action.

**Setup (5 minutes before the session)**
- Start the app (README "Quick start") and open `http://127.0.0.1:8000/#/dashboard/demo` in Chrome, Edge or Safari. This is the saved real analysis for a fictional applicant, so no paid model call happens.
- Reload once (Ctrl+Shift+R) so the weekly plan starts with nothing marked done.
- Have a stopwatch ready. Don't show the tester the answer key.
- **Consent:** verbal consent; no names, emails or other identifiers recorded. Use the tester code T1. The tester uses the fictional profile, never their own data.

## Scenario (read aloud, or give the tester a copy)
> "Imagine you're Ama, a senior audit associate from Ghana with five years at a Big Four firm and then in the public sector. You want to move into management consulting in the United States after an MBA, and you'll need U.S. work authorization after graduating. Your budget is about $140,000 a year, and you can spend about 10 hours a week on applications. You haven't taken the GMAT or GRE yet. AdmitCompass has already analysed your profile — this page shows its results. Please think aloud as you go."

## Script (facilitator)
1. "Take a minute to look at the page however you like." *(Start the stopwatch when the tester first looks at the page.)*
2. **Task 1 — strongest programs:** "Which program or programs fit Ama's goal best?"
3. **Task 2 — GRE or GMAT:** "Should Ama take the GRE or the GMAT? What should she do next about the test?"
4. **Task 3 — top profile gap:** "What is the most important gap in Ama's profile right now?"
5. **Task 4 — this week's action:** "What should Ama do this week?" *(Stop the timer for "time to next action" when the tester states the week-1 action, or says they can't find it.)*
6. **Wrap-up questions:**
   - "Was anything confusing?"
   - "If you could change one thing, what would it be?"
   - "Is there one sentence about the tool I may quote anonymously?"
- **Facilitator rules:** don't point at the screen or hint. If the tester asks a question, answer only "What would you do if I weren't here?" and record it as a clarification question. Stop any task after 3 minutes and mark it "not completed".

## Answer key (facilitator only — taken from the saved analysis, 2026-10-24)
| Task | Correct answer | Where it is on the page |
|---|---|---|
| 1. Strongest programs | **MIT Sloan** (strong career fit). Yale SOM and Duke Fuqua are moderate fits. | Top summary "School shortlist" and the Shortlist cards |
| 2. GRE or GMAT | **Undecided:** no diagnostic scores yet, so take one timed practice test of each, then choose one. Neither test is recommended just because it's more common. | Decision 2 "GRE or GMAT" and the GRE or GMAT card |
| 3. Top profile gap | **"No test score or preparation baseline; all three programs require a test."** (Credit also given for naming the test-score gap in other words.) | "Profile gaps", item 1 |
| 4. This week's action | **"Use up to 10 hours for timed GMAT and GRE diagnostics, then select one test."** | Decision 3 "Next action this week" and Week 1 in "This week's plan" |

Scoring per task: **2** = correct without help · **1** = partly correct, or correct after a clarification question · **0** = incorrect or not completed.

## Measurements
- **Time to identify the next action:** seconds from the first look at the page to stating the Task 4 answer.
- **Clarification questions:** count, and write each one down.
- **Completion:** per task, completed / not completed, plus the 0–2 score.
- **Confusion moments:** what the tester hesitated over, scrolled back to, or misread, written as observed.
- **One direct quote:** word for word, with the tester's permission.
- **One suggested improvement:** in the tester's words.

---

## Results — T1 (fill in only after a real session)
```
Tester code: T1        Date: ____________        Browser / device: ____________
Facilitator: ____________   Consent given (verbal): yes / no
Tester background (no identifiers; e.g. "MBA applicant, international"): ____________________

Time to identify the next action: ______ seconds   (stopped at: stated / gave up at 3:00)

Task 1  Strongest programs   Answer given: ______________________________   Completed: yes / no   Score: 0 / 1 / 2
Task 2  GRE or GMAT          Answer given: ______________________________   Completed: yes / no   Score: 0 / 1 / 2
Task 3  Top profile gap      Answer given: ______________________________   Completed: yes / no   Score: 0 / 1 / 2
Task 4  This week's action   Answer given: ______________________________   Completed: yes / no   Score: 0 / 1 / 2
Total score: ____ / 8

Clarification questions (count: ___):
  1. ______________________________________________________________
  2. ______________________________________________________________

Confusion moments (as observed):
  - ______________________________________________________________
  - ______________________________________________________________

Direct quote (verbatim, permission given: yes / no):
  "______________________________________________________________"

Suggested improvement (tester's words):
  ______________________________________________________________
```

## Reporting rules
- Report only what was observed. With one tester, describe the results; don't generalize them to all users.
- If a field wasn't observed, write "not recorded".
- The quote goes in the report only with permission, attributed as "T1, prospective MBA applicant" (no name).
- **Limitations to state with any result:** one tester; the tester uses a fictional profile and a saved analysis (not a live run of their own); the facilitator may influence behaviour; time includes think-aloud, which slows people down.

---

## Recorded results — three testers (T1, T2, T3)

**Source of these results:** feedback that three real testers gave the project owner, reported on 2026-10-24 as **paraphrased recollections**. It was not captured with the template above or a standardized questionnaire, and no wording was recorded verbatim, so nothing below is a quotation. Testers are anonymous and identified only by code.

**Profile used in the sessions:** not recorded. (It isn't documented whether the testers used the fictional saved Sample Analysis described in this protocol or entered their own information.)

| Field | T1 | T2 | T3 |
|---|---|---|---|
| Broad role or relationship | not recorded | not recorded | not recorded |
| Task 1 — strongest programs (completed?) | not recorded | not recorded | not recorded |
| Task 2 — GRE or GMAT (completed?) | not recorded | not recorded | not recorded |
| Task 3 — top profile gap (completed?) | not recorded | not recorded | not recorded |
| Task 4 — this week's action (completed?) | not recorded | not recorded | not recorded |
| Score out of 8 | not recorded | not recorded | not recorded |
| Time to find this week's action | not recorded | not recorded | not recorded |
| Clarification questions (number and wording) | not recorded | not recorded | not recorded |
| Confusion moments | not recorded | not recorded | not recorded |
| Approved verbatim quote | not recorded | not recorded | not recorded |
| Feedback summary (paraphrased, not verbatim) | Reported that AdmitCompass was easy to use. | Liked the voice command functionality. | Appreciated that someone without prior experience applying to schools could use AdmitCompass to explore opportunities and learn about the application process. |
| Suggested improvement | not recorded | not recorded | not recorded |

### Aggregate findings
- **Three real testers** provided feedback.
- **T1** highlighted ease of use.
- **T2** highlighted voice interaction.
- **T3** highlighted usefulness for applicants unfamiliar with school applications.
- **Overall impression:** all three reported favorable impressions in the feedback available.
- **No quantitative results:** task completion, timing and scores weren't recorded, so none are reported.
- **No recurring confusion points or improvement suggestions** were recorded.

### Limitations
- **Only three testers.**
- **Convenience sample:** testers weren't recruited to represent MBA applicants as a whole.
- **Profile used is not recorded:** it isn't documented whether testers used the fictional saved applicant profile or their own information.
- **Possible facilitator influence** on what testers did and said.
- **Recalled feedback:** feedback was recalled after the sessions, not captured with a standardized questionnaire or the template above, and no wording was recorded verbatim.
- **Early qualitative evidence:** this is early qualitative usability evidence, not a representative user study, and it supports no claims about effect size, speed or accuracy.
