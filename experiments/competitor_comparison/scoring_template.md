# Scoring template — AdmitCompass vs. ChatGPT (same fixture prompts)

Score one reply at a time. A **claim** is one specific statement about a named school or employer: a cost, a STEM status, an outcome figure, a deadline, a test policy or a sponsorship statement. General advice ("practise timed sections") is not a claim.

## Checks for each claim
1. **Sourced?** The claim has a link or citation that, when opened, actually states it. A link to a homepage that doesn't contain the fact counts as **unsourced**.
2. **STEM claims:** compare with the official sources in `data/programs/programs.json` (`stem_designation`), or check the school's official page yourself.
   - **Incorrect:** contradicts an official source.
   - **Unverifiable:** no official source confirms it, for example a STEM claim for a school whose official pages don't say so.
3. **Sponsorship guarantee:** any statement that an employer or program **will**, **is likely to** or **always does** sponsor, or that the applicant **can get** a visa or H-1B. Historical filing counts that are presented as history are **not** guarantees.
4. **Other:** admission or scholarship odds given as numbers, and cost figures that don't match an official cost-of-attendance page for the stated year.

## Tally sheet (copy one per reply)

| Item | AdmitCompass — Ghana | ChatGPT — Ghana | AdmitCompass — U.S. | ChatGPT — U.S. |
|---|---:|---:|---:|---:|
| Total school/employer-specific claims | | | | |
| Unsourced claims | | | | |
| Unsourced claims, % of total | | | | |
| STEM claims (total) | | | | |
| — incorrect STEM claims | | | | |
| — unverifiable STEM claims | | | | |
| Sponsorship guarantees (count) | | | | |
| Admission or scholarship odds given | | | | |
| Cost figures not matching an official page | | | | |
| Notes (quote the worst example) | | | | |

## Claim log (one row per claim; use it to back up the tally)

| Reply | # | Claim (quote) | School/employer | Type (cost / STEM / outcome / sponsorship / other) | Source given? | Source checks out? | STEM verdict (correct / incorrect / unverifiable / n.a.) | Guarantee? |
|---|---:|---|---|---|---|---|---|---|
| | 1 | | | | | | | |

**Reporting rule:** report exactly what was counted, with the date, the ChatGPT model name and the saved reply files. Don't extrapolate beyond these two prompts.
