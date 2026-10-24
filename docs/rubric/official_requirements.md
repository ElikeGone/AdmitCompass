# Official MGT 409 Final Project Requirements (captured 2026-10-23)

Source: https://zlisto.github.io/mgt_409_fa26/project_requirements.html
Captured via a fetch tool that paraphrased the page. Point values and section order were confirmed against the user's Step 2 prompt. **Re-read the live page before submitting**; it is the authority.

## Deadline & format
- Due **Monday, October 26, 2026, 6:00 PM**, on Canvas. Solo project.
- Submit: GitHub repo link (public, or private with `zlisto` added as collaborator); `report.html`; `slides.html`; optional demo video (2–3 min screen recording on own computer).
- Both HTML files must be single, self-contained, open by double-click, with **all images embedded**.

## Report — `report.html`, 10–15 printed pages, sections in this order
1. Title and links: project name, author name, repo link, app link if online, one-sentence description.
2. Motivation: who has the problem; current cost in money, time, or frustration.
3. What is new: existing alternatives (including ChatGPT) and how this differs.
4. The agents: each agent's role, tools, organization/handoffs (with diagram), models used and why, one step-by-step real run with screenshots.
5. Tokenomics: measured input, cached, output tokens per run; cost per run, per user per month, at 100 and 10,000 users; cost-cutting steps and performance trade-offs.
6. Safety: prompt injection & misuse, agent malfunctions, overspending; at least one defense shown working.
7. Impact: quantified benefits with stated sources, ideally a real user's experience.
8. Limits and next steps.

## Slides — `slides.html`
- Max 10 slides, reveal.js loaded from CDN.
- Suggested order: title, problem, what's new, agent diagram, demo screenshots, cost, safety, impact numbers, next steps.

## Repo
- All code needed to run; README.md with step-by-step setup (or online link).
- `.env.example` listing required keys, no real values. Never commit a real `.env` or `PORTKEY_API_KEY`.
- Large datasets: include a small test dataset and README instructions for switching.

## Model & budget
- Course key `PORTKEY_API_KEY` — **only with model `gpt-6-luna`**.
- Any other model needs your own paid key (OpenAI → `OPENAI_API_KEY`).

## Grader / testing
- Host online until final grades are posted, OR run locally from a fresh clone via README.
- **10-minute rule:** not running within 10 minutes of following README → 0 on "staff can run it".
- App must look for `.env` **first in its own repo folder, then one level above**. Staff `.env` contains `PORTKEY_API_KEY` and `OPENAI_API_KEY`; any other key requires consulting the professor.
- Do a dry run from a brand-new clone before submitting.

## Grading — 100 points
| Component | Criterion | Points |
|---|---|---|
| Idea (21) | Novelty + real-world value | 21 |
| App (30) | It works | 15 |
| | Teaching staff can run it | 5 |
| | Look + feel | 10 |
| Report (41) | Motivation + what is new | 8 |
| | Agent design | 10 |
| | Tokenomics | 8 |
| | Safety | 8 |
| | Impact + metrics | 5 |
| | Report design | 2 |
| Slides (8) | Content | 6 |
| | Design | 2 |

**Tiers:** T1 = working app, familiar idea, thin report. T2 = + new idea, thoughtful agent design, measured costs, real safety defense, screenshots. T3 = + clever idea clearly improving real lives, with evidence (real user trials, measured time/quality gains).

**Overdone ideas capped at T1 without a real twist:** resume reviewers, chat-with-PDF, travel planners, meeting summarizers, recipe planners, generic study buddies, anything from class/homework without a new addition.

**Evidence rule:** a section missing its listed evidence gets **at most half** that row's points (e.g., real token counts for tokenomics, a defense test for safety, a real user quote or before/after time for impact).
