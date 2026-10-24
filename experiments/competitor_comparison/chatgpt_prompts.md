# ChatGPT prompts for the two demo fixtures

**How to run (for a fair comparison):**
1. Open a **new chat** with memory and custom instructions off (or use a temporary chat).
2. Record the model name shown in ChatGPT and the date and time.
3. Paste one prompt exactly as written below, then save the full reply, including any links, into `chatgpt_outputs/`:
   - `chatgpt_outputs/ghana.md` for Prompt A;
   - `chatgpt_outputs/us.md` for Prompt B.
4. Use a new chat for the second prompt.
5. Score each reply with `scoring_template.md`.

The prompts give ChatGPT the same facts AdmitCompass received (`data/fixtures/applicant_audit_consulting_ghana.json` and `applicant_domestic_tech_us.json`) and ask for the same outputs.

---

## Prompt A — fixture-audit-consulting-ghana

```
I'm a citizen of Ghana and I will need U.S. work authorization after an MBA. Background: BSc in Accounting (first class honours, Ghana), about 5 years in audit — first at a Big Four firm, now in the public sector; I'm a senior audit associate. Goal: management consulting at a strategy consulting firm in Boston. Budget: about $120,000 per academic year (savings plus loans; I'll apply for scholarships). I haven't started the GMAT/GRE. I want to start in 2027, my first application is about 12 weeks away, and I have about 10 hours per week.

Please:
1. Recommend 3–5 U.S. full-time MBA programs that fit this career goal, and explain why each fits.
2. For each program give: total cost of attendance per year, whether the MBA is STEM-designated, employment outcomes, and evidence about employer visa (H-1B) sponsorship for consulting roles in Boston.
3. Tell me whether the GMAT or GRE is better for me.
4. Give me a week-by-week plan for the next 12 weeks.
Cite a source for every specific fact.
```

## Prompt B — fixture-domestic-tech-us

```
I'm a U.S. citizen, so I don't need any work authorization. Background: BS in Mechanical Engineering (3.5–3.7 GPA), about 6 years in hardware and systems engineering at a consumer electronics company. Goal: product manager at a technology company in Seattle. Budget: about $150,000 per academic year (savings plus some employer support). I'm preparing for the GMAT/GRE but have no score yet. I want to start in 2027, my first application is about 10 weeks away, and I have about 12 hours per week.

Please:
1. Recommend 3–5 U.S. full-time MBA programs that fit this career goal, and explain why each fits.
2. For each program give: total cost of attendance per year, employment outcomes for product management roles, and anything relevant about recruiting in Seattle.
3. Tell me whether the GMAT or GRE is better for me.
4. Give me a week-by-week plan for the next 10 weeks.
Cite a source for every specific fact.
```

---

## Matching AdmitCompass outputs (already saved)
| Fixture | Saved four-agent run | Live UI run |
|---|---|---|
| Ghana | `experiments/agent_runs/20261024T020115Z_fixture-audit-consulting-ghana/` | screenshots in `deliverables/screenshots/final/task3_*` |
| U.S. | `experiments/agent_runs/20261024T020259Z_fixture-domestic-tech-us/` | — |

**Note for scoring:** AdmitCompass demo runs use only the 5 programs with detailed evidence; ChatGPT can recommend any school. Score each claim on its own merits. Don't penalize ChatGPT for naming different schools.
