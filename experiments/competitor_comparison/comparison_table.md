# Comparison with alternatives (placeholder — to be completed)

**AdmitCompass** cells come from this repository, with the evidence named. **Every other cell is a placeholder.** Fill it only from your own testing or a dated source, and record that source, so nothing in the final report is assumed.

| Capability | AdmitCompass | ChatGPT | GoScholar AI | GMAT Club | Poets&Quants | ApplyBoard |
|---|---|---|---|---|---|---|
| Starts from the applicant's career goal (career-first matching) | Yes: the Pathway Matcher builds target roles and then a shortlist (`experiments/agent_runs/`) | _TBD (from your ChatGPT test)_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Every school-specific fact linked to a source, or marked unknown | Yes: grounding checks drop unsourced facts (`tests/test_agents.py`, `experiments/safety/`) | _TBD: unsourced % from `scoring_template.md`_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| STEM status verified against official sources | Yes: STEM verified with sources for the programs in `data/programs/programs.json` | _TBD: incorrect/unverifiable STEM claims_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Employer-specific H-1B evidence | Yes: DOL FY2025 LCA filings joined to official employer lists (`data/sponsorship/`) | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Blocks sponsorship guarantees | Yes: the `sponsorship_guarantee` rule; safety scenarios S25 and S26 pass | _TBD: guarantee count_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Official cost vs. estimates kept separate | Yes: official, reported and estimate lines (`experiments/research/research_report.md`) | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Week-by-week application plan | Yes: the Strategy Planner (`experiments/agent_runs/*/report.json`) | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Admission odds | Never given (blocked; safety scenario S07) | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Cost to the user | Free in this prototype (operating cost in `experiments/tokenomics/clean_runs_analysis.md`) | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Source / date checked | This repo, 2026-10-24 | _date + model_ | _URL + date_ | _URL + date_ | _URL + date_ | _URL + date_ |
