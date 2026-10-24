# Screenshots (captured 2026-10-23 from the running local app)

| File | What it shows | How it was captured |
|---|---|---|
| 01_home.png | Overview / landing page | Headless Edge, 1440 px, `http://127.0.0.1:8000/#/` |
| 02_profile_review_demo_applicant_A.jpg | Profile review step with fictional applicant A loaded | Browser pane during the UI test |
| 03_live_run_view_UI_REPLAY_of_saved_events.jpg | Live-analysis screen mid-run | **UI test only:** browser `fetch` was stubbed to replay the real saved run's events in batches. No model call was made, and it is not a new run. |
| 04_results_programs.png | Saved demo results: comparison table + program cards + sources | Headless Edge, `#/results/demo/programs` |
| 05_results_strategy.png | GMAT/GRE guidance, gaps, weekly plan, roadmap | Headless Edge, `#/results/demo/strategy` |
| 06_results_skeptic.png | Skeptic review, findings, safeguards, unresolved risks | Headless Edge, `#/results/demo/skeptic` |
| 07_results_trace.png | Real token usage, runtime, per-agent table, chronological trace | Headless Edge, `#/results/demo/trace` |
| 08_run_failure_state_UI_TEST_stub.jpg | How a budget-stopped run is displayed | **UI test only:** stubbed response with synthetic events; no real run |

All results screenshots show the saved real run `experiments/agent_runs/20261023T180104Z_fixture-tech-pm-india` (fictional applicant).
