# Ask AdmitCompass — AI copilot (Step 12)

## What the user sees
- An **Ask AI** button fixed at the bottom right of every page. It opens a side panel on desktop and a bottom sheet on phones.
- **Suggested questions** that depend on the page, and clicking one sends it. On the dashboard the suggestions are, for example, "Why is MIT Sloan recommended for this profile?" and "What should I do next?". After an answer, two follow-up suggestions appear.
- **Visible context chips**, which the user can remove: "Sample analysis", the selected program, or the programs being compared. Only these explicit ids are sent with a question.
- **Each answer shows:**
  - a type badge: cited / general guidance / sourced + general / refused;
  - numbered citation links to official pages, plus a source list;
  - a collapsible "What's uncertain";
  - a next step;
  - the model calls, tokens and seconds used.
- **New conversation** (＋). The conversation is kept in `sessionStorage` for the current tab only; the server stores no chat history.
- **Keyboard:** Enter sends, Shift+Enter adds a new line, and Escape closes the panel and returns focus to the launcher. The log is a polite live region. Reduced motion is respected.

## How an answer is produced (`backend/app/copilot/`)
1. **Screening** (`service.screen_input`):
   - Personal identifiers (email, phone, ID or passport numbers, date of birth) are rejected with 422 before anything is sent.
   - Prompt-injection patterns get a fixed refusal, with no model call.
2. **Limits:**
   - Questions are at most 1,000 characters.
   - At most 20 history turns are accepted; only the last 6 are used, each cut to 600 characters.
   - Context ids must match strict patterns.
   - Per client: 6 questions per minute and 40 per hour. Each conversation allows 20 messages, and the server allows 200 per day. All are in memory and configurable by env.
   - Requests must come from the same origin.
3. **Deterministic retrieval** (`retrieval.py`):
   - Schools named in the question come first, then schools named in the previous question, then the UI-scoped program(s), then "which programs…" across all programs, then the saved analysis's shortlist.
   - Topic keywords pick the facts (STEM, visa, cost, outcomes, tests, deadlines, next steps). The limit is 40 facts.
   - Unknown facts are included as "unknown" (checked or not checked), so gaps are explicit.
4. **One model call** (gpt-6-luna via Portkey's Responses API, reasoning effort low, at most 900 output tokens, JSON):
   - It receives the rules, the question, the recent turns, the minimal saved-analysis summary (no identifiers) and only the retrieved facts.
   - Those facts are labeled as untrusted data.
5. **Grounding** (`service.ground`):
   - Every cited id must be one of the retrieved ids.
   - Every number of 10 or more must appear in the cited evidence, the saved analysis or the user's own questions. Years 2000–2040 are allowed.
   - The existing `risky_language` rules block admission or scholarship odds, guarantees, "will sponsor" and visa-eligibility assertions.
6. **One repair call** with the specific problems listed. If the answer still fails, a **deterministic fallback** lists the retrieved sourced facts and the unknowns. Unverified model text is never shown.
7. **Citations:** the server resolves them to `{n, title, url, excerpt}` and turns `[ev-…]` into `[n]`.

## Modes and keys
- `AC_COPILOT_MODE=mock` uses an offline mock model that makes **no network call**. Its answers are labeled "[Mock model — no AI call was made]" and show a Mock badge. The `admitcompass-mock` entry in `.claude/launch.json` uses it.
- **Default (live)** uses the course `PORTKEY_API_KEY` on the server. The key is never sent to the browser; `/api/copilot/status` only reports whether a key exists.
- **No key** gives a 503 with a plain message. An API failure or timeout gives a 502 ("try again"), with no internal details.

## Evidence
- `tests/test_copilot.py`: 22 tests, all with the model mocked. They cover retrieval, citation grounding, repair and fallback, blocked claims, unknown sponsorship and cost, injection, PII, input and rate limits, CSRF/origin, missing key and API failure, and mock mode.
- `experiments/copilot/sample_conversations.md`: 7 labeled mock conversations, including a follow-up, an injection attempt and a PII rejection.
- `experiments/copilot/token_budget.md`: prompt sizes measured from the real prompts (about 1.5k–3.9k input tokens), the output cap and worst cases.

## Limitations
- **No live answers yet.** No gpt-6-luna call was made for the copilot (per your instructions), so live answer quality, the real token counts and latency are **unverified**. A small, approved live test is the next step.
- **Strict number grounding** can push correct answers into the fallback, for example when general knowledge such as "12 months" is stated without evidence. Then the user sees sourced facts rather than prose.
- **Keyword retrieval:** school and topic matching uses keywords. Unusual phrasings or school nicknames may miss, in which case the shortlist or a general answer is used.
- **Saved analysis only:** "this profile" context exists only for the saved sample analysis. A user's own live analysis isn't wired into the copilot yet.
- **In-memory limits:** rate limits reset on restart and aren't shared across processes.
- **History is browser-supplied.** A modified client could send fake "assistant" turns. They're treated as untrusted context and every answer is still grounded against the store.
