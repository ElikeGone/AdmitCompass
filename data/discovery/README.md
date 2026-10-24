# Discovery index (needs verification)

`discovered_programs.json` is a **periodically built index, not a live search.** Built 2026-10-23 by `scripts/build_discovery_index.py` from the raw collection notes in `raw/`.

## What a discovered record is
Proof that a real US full-time MBA program exists, where we learned it (one official university page), and where it is. Fields: university, school, program name, degree type, format, city/state with the basis for them, provenance URL, page title, short excerpt, discovery date, whether the page was actually fetched, and the verification status.

**Not included, by design:** tuition, cost of attendance, employment outcomes, STEM designation, admissions statistics or odds, sponsorship. The schema forbids these fields.

## Status values
- `needs_verification`: the official page was fetched and confirms the program exists (21 records).
- `not_confirmed`: an official URL was found by search, but fetching it failed (3 records: Columbia and Michigan Ross returned HTTP 403; Indiana Kelley failed with a TLS certificate error). These have no location.
- `verified`: **never assigned here.** Verified programs live only in the evidence store (`data/programs/`).

## Source and method
- **Source:** official program pages on each university's own domain (e.g. `gsb.stanford.edu`, `mays.tamu.edu`).
- **Method:** 3 research agents (Claude Code subagents), each given 8 named programs. Each one web-searched for the official page, fetched it, and recorded an excerpt confirming a full-time MBA. Location comes from the fetched page, or from a second official page on the same domain (`location_basis` says which).
- **Seed list:** chosen by the author (24 well-known full-time programs outside the verified six). Coverage is therefore **not** a complete or representative census of US MBA programs.

## AACSB directory (evaluated, not used for records)
`https://www.aacsb.edu/accredited` was fetchable and listed 1,095 accredited schools with school name, college, city, state and country, plus program filters. No download or API was seen, the terms of use weren't reviewed, and whether it's fully server-rendered wasn't established. It's a good candidate as a *seed list* for future expansion (each school would then be confirmed on its own official program page). It's not suitable as a source of program facts.

## Known weak points (kept visible in the records)
- Wharton: city only (no state on the fetched page). Haas: no location on the fetched pages.
- UNC: location inferred from an FAQ that names "Chapel Hill" and "North Carolina" separately.
- NYU and Vanderbilt: excerpts are short headings or snapshot labels, not full sentences.
- Tuck: the excerpt comes from the official FAQ page (noted in the record).

## Maintenance
Re-run collection each term. Re-fetch every `provenance_url`; mark records `not_confirmed` if the page disappears; add new programs from a seed list (e.g. AACSB) only after their official page is fetched. Promotion to the verified evidence store requires the full per-fact evidence process (`scripts/build_dataset.py` pipeline: per-field official sources, dates, excerpts, audit), never a simple status change.
