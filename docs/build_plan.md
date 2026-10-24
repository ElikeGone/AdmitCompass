# Build Plan

**Hard deadline: Monday, October 26, 2026, 6:00 PM (Canvas).** Today: Friday, Oct 23. Internal target: everything submitted by **Mon 2:00 PM** (4-hour buffer).

Principle: ship a simple working, differentiated MVP first (Sat midday), then measure, test safety, test with users, and write — those carry ~46 of 100 points and need a working app to produce evidence.

## Milestones
| # | Milestone | Depends | Acceptance test | Target |
|---|---|---|---|---|
| 1 | Foundation & requirements | — | Approved | Fri Oct 23 ✅ (pending review) |
| 2 | Official requirements alignment | 1 | Rubric/plan/decisions approved | Fri Oct 23 |
| 3 | **Skeleton + LLM smoke test**: `.env` loader (repo → parent), Portkey client for `gpt-6-luna`, token/cost logger, Pydantic schemas (`Claim`, `Evidence`, agent outputs), `requirements.txt` | 2 | One real `gpt-6-luna` call returns structured output; usage (input/cached/output) logged | Fri night |
| 4 | **Evidence dataset**: 6–8 programs, hand-verified facts with URL + retrieved date (requirements, STEM CIP, tuition, outcomes, sponsorship evidence); 2–3 fixture profiles | 3 | Validator: every `verified_fact` has URL + date; no STEM=true without source | Sat AM |
| 5 | **Agents + orchestrator** (4 agents, see decisions ADR-007) with tools, handoffs, Skeptic revision loop, cost cap | 3,4 | Fixture profile → full labeled report; trace JSON saved; run cost under cap | Fri Oct 23: ✅ complete real run (`20261023T180104Z`), 79 tests pass, post-run audit ok |
| 6 | **UI**: intake form, shortlist, evidence cards w/ labels, test guidance, gap plan + weekly schedule, roadmap, Skeptic panel, trace/cost panel | 5 | Full demo flow in browser locally | Fri Oct 23: ✅ built and browser-tested on the saved run; live UI run not exercised with a paid call |
| 7 | **Fresh-clone test #1** (`.env` one level above clone), timed ≤10 min | 6 | Documented time and steps in `experiments/fresh_clone_test.md` | Sat night |
| 8 | **Measured evidence**: tokenomics baseline vs optimized; safety tests; competitor comparison; one full real trace with screenshots | 6 | Files in `experiments/` from real runs | Fri Oct 23: ✅ safety 24/24, tokenomics, optimization, performance; competitor comparison + fresh optimized run pending |
| 9 | **User testing / timed baseline**: 1–3 real applicants or timed manual vs app | 6 | Quotes/times recorded with consent | Sun PM — protocol ready (`docs/user_test_protocol.md`); needs the user to recruit testers |
| 9b | **AdmitCompass 2.0** hybrid redesign + discovery foundation (user feedback) | 6 | Browser-tested journey, mobile, 151 tests | Fri Oct 23: ✅ |
| 10 | **Deliverables**: `report.html` (8 sections, exact order, 10–15 pages, embedded images), `slides.html` (≤10, reveal.js CDN), optional video | 8,9 | Open each HTML standalone from another folder; images visible; print preview page count | Sun night – Mon AM |
| 11 | **Final fresh-clone dry run**, repo public (user action), Canvas submission | 10 | Clean clone runs in ≤10 min; no secrets in repo | Mon by 2 PM |

## Critical path
3 → 4 → 5 → 6 → 7 → 8 → 10 → 11. User testing (9) runs in parallel with 8 once the app works.

## Cut order if late
1. Optional demo video → 2. Roadmap visual polish → 3. Programs beyond 6 → 4. Second Skeptic revision pass → 5. Live web fetching (already out of MVP).
Never cut: fresh-clone test, measured tokens, one working safety defense, impact evidence (each is a half-points cap if missing).

## Deliverables checklist
- [ ] Public GitHub repo (user creates/publishes; I will not publish) with README + `.env.example`
- [ ] `deliverables/report.html` — self-contained, 10–15 printed pages, sections 1–8 in exact order, base64-embedded images
- [ ] `deliverables/slides.html` — reveal.js from CDN, ≤10 slides, base64-embedded images
- [ ] Optional 2–3 min demo video
- [ ] Both HTML files verified by opening a copy from a different folder
