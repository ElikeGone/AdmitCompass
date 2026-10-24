# Copilot token and latency budget

Measured from the exact prompts the live model would receive for the sample questions (tokens ≈ characters ÷ 4; the real tokenizer count will differ somewhat). No live call was made, so latency is not measured.

| Question | Prompt chars | ≈ Input tokens |
|---|---:|---:|
| Why is MIT Sloan recommended for this profile? | 8,864 | 2,216 |
| Can this applicant afford it? | 5,875 | 1,469 |
| Compare Yale and Booth for my career goal. | 12,739 | 3,185 |
| what about cost? | 6,841 | 1,710 |
| Which programs have verified STEM status? | 15,744 | 3,936 |
| What do we know about visa sponsorship? | 10,231 | 2,558 |
| What should I do next? | 8,483 | 2,121 |

- Largest prompt ≈ 3,936 input tokens (all-program STEM question, 28 facts).
- Output cap: 900 tokens per call (reasoning effort low; reasoning tokens count toward it).
- Calls per question: 1 normally; 2 if the first answer fails grounding (one repair); 0 for refused or rejected input.
- Worst case per question ≈ 8,472 input + 1,800 output tokens.
- Limits: 1,000-character questions; 6 history turns × 600 chars; 40 facts; 6 questions/minute and 40/hour per client; 20 messages per conversation; 200 per server per day (all configurable by env).
- Cost: unknown — no published gpt-6-luna price (same as the agent runs).
- Latency: not measured (no approved live call). Earlier single agent calls in the saved run took a few seconds each at low reasoning effort; expect a similar order of magnitude, plus a second call when a repair is needed.