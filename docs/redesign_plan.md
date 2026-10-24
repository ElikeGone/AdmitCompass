# AdmitCompass 2.0: hybrid redesign plan

## Audit of the Step 6/7 interface (sources of overload)
Screens reviewed: `deliverables/screenshots/01–07` (Step 6) and the live app.

| Problem | Where | Effect |
|---|---|---|
| Too many visual containers: nearly every element is a bordered, shadowed card; cards nested inside cards (program card → fact tiles → source cards) | Results, home | Everything looks equally important; heavy "dashboard" feel |
| Badge overload: 4–6 pills per program (fit, STEM, budget, sponsorship, labels, verification levels) plus claim-label chips on every line | Program cards, tables | The eye has nowhere to rest; labels compete with content |
| Typography: one serif (Palatino/Georgia fallback) used for every heading, with a system sans for the rest; dense 15.5 px body; uppercase eyebrows everywhere | All | Dated and busy, weak hierarchy |
| Agent machinery up front: the 4-agent panel on the landing page, an "Agent trace & usage" tab at the same level as results, token tiles, safeguard lists | Home, results | Technical detail dominates the applicant's question ("which program, why?") |
| Long, flat result pages: comparison table + 4 very long cards, each with tradeoffs + 5–6 analyst claims + 6 fact tiles + 8 sources | Programs tab | Several screens of scrolling before the second program |
| Plan buried: 10-week list and gaps shown at equal weight | Strategy tab | The "what do I do next" answer is not obvious |
| Six schools presented as the whole product | Home, review | The product feels small and constrained |
| Wizard shows 10 fields at once on step 1 | Profile | Feels like a form, not a conversation |

## Design direction: hybrid
Editorial landing → calm, conversational onboarding → modern, interactive discovery and results → evidence and agent detail on demand.

### Design system
- **Colours:** ivory `#F8F7F3` (page), navy `#18283D` (text, primary), muted teal `#397F79` (accent, links, focus), sage `#E7EBE7` (quiet surfaces, selected states). Amber and red only for genuine warnings.
- **Type:** *Instrument Serif* only for display headings (h1/h2 on landing and section titles). *DM Sans* for everything else. Self-hosted woff2 with local fallbacks (Georgia / system sans).
- **Scale:** 13 / 15 / 17 / 20 / 28 / 40 / 64 px; body 17 px with 1.6 line height; max text width ~68 characters.
- **Spacing:** 4-px base (8, 12, 16, 24, 32, 48, 72, 96).
- **Surfaces:** mostly borderless sections on ivory; white cards only for interactive items (program cards, steps), with a 1 px hairline and no heavy shadow. Radius 14 px for cards, 999 px for buttons.
- **Badges:** at most two per program card (career fit + one status). Claim labels shown as quiet text tags only inside expanded detail.
- **Breakpoints:** 1100 / 820 / 560 px; touch targets ≥ 44 px.

### Information architecture
| Route | Purpose |
|---|---|
| `#/` | Editorial landing: one headline, short promise, one primary CTA ("Start your assessment"), a secondary "See a sample analysis", "How it works" in three plain steps |
| `#/start` | Conversational onboarding: 6 short steps (2–4 fields each), progress bar, examples, review/edit, explicit budget-period choice |
| `#/explore` | Explore Programs: search, filters (evidence status, state, STEM verified, max cost of attendance), grounded sorting, readable cards; verified collection + discovered index with "Needs verification" |
| `#/results/:id` | Your shortlist: per program "why it fits your career", cost vs budget, STEM evidence, the single most important uncertainty; "Details & sources" expander |
| `#/results/:id/plan` | Roadmap: next 3 priority actions first, then the full weekly checklist and phases |
| `#/results/:id/evidence` | Evidence & Risks: Skeptic review, safeguards, citations, agent trace, tokens (secondary) |
| `#/how` | How AdmitCompass works: agents, grounding, limits, data coverage |
| `#/run/:id` | Calm live progress: four steps, one line of current activity, expandable log |

### Before → after (key changes)
- Landing: agent-heavy hero + 4 trust cards + coverage card → one editorial hero, three-step explainer, evidence promise in one sentence.
- Profile: 4 dense steps → 6 conversational steps, each with an example.
- Results: comparison table + long cards + 4 equal tabs → short "fit summary" cards with progressive disclosure; Plan and Evidence as separate, clearly secondary sections.
- Six schools → curated verified collection + discovered index in Explore, clearly labelled.

## Out of scope this step
No new paid runs; discovered programs are not fed to the agents; no final report/slides.
