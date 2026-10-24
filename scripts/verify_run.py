"""Deterministic post-run audit of a saved agent run (no model calls).

Usage: .venv\\Scripts\\python scripts\\verify_run.py experiments\\agent_runs\\<run folder>
Writes <run folder>/verification.json.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.agents.grounding import _numbers_from_value, iter_strings, numbers_in  # noqa: E402
from backend.app.schemas.applicant import ApplicantProfile  # noqa: E402
from backend.app.schemas.programs import FACT_NAMES  # noqa: E402
from backend.app.tools.evidence_store import EvidenceNotFoundError, EvidenceStore  # noqa: E402

COMPARE_WORDS = re.compile(r"\b(higher|lower|better|worse|stronger|weaker|outperform|beats?|more than|less than|ranks?)\b", re.I)


def main(run_dir: Path) -> int:
    store = EvidenceStore.load()
    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    profile = ApplicantProfile.model_validate(json.loads((run_dir / "input_profile.json").read_text(encoding="utf-8")))
    prof_nums = _numbers_from_value(profile.known_fields())
    result = {"run_dir": run_dir.name, "programs": [], "problems": []}
    for rec in report["recommendations"]:
        pid = rec["program_id"]
        allowed = set(prof_nums)
        for name in FACT_NAMES:
            f = store.get_fact(pid, name)
            allowed |= _numbers_from_value(f.value) | numbers_in(f.period or "") | numbers_in(f.definition or "")
            for e in f.evidence:
                allowed |= numbers_in(e["excerpt"])
        ev_ids = sorted({i for c in rec["analyst_claims"] for i in c["evidence_ids"]} |
                        {i for f in rec["facts"] for i in f["evidence_ids"]})
        bad_ids = []
        for i in ev_ids:
            try:
                if store.fact_for_evidence(i)[0] != pid:
                    bad_ids.append(i)
            except EvidenceNotFoundError:
                bad_ids.append(i)
        free_text = {k: rec[k] for k in ("fit_rationale", "tradeoffs", "affordability_basis", "flags")}
        free_text["claims"] = [c["text"] for c in rec["analyst_claims"]]
        unsupported_nums = sorted({n for _, t in iter_strings(free_text) for n in numbers_in(t)
                                   if n >= 10 and n not in allowed})
        employment_comparisons = [t for _, t in iter_strings(free_text)
                                  if re.search(r"employment|salary|placement|offer", t, re.I) and COMPARE_WORDS.search(t)]
        verified_claims = [c for c in rec["analyst_claims"] if c["label"] == "verified_fact"]
        row = {"program_id": pid, "evidence_ids": ev_ids, "evidence_ids_invalid": bad_ids,
               "verified_claims": len(verified_claims),
               "verified_claims_without_evidence": sum(1 for c in verified_claims if not c["evidence_ids"]),
               "numbers_not_in_store_or_profile": unsupported_nums,
               "possible_employment_comparisons": employment_comparisons,
               "stem_status_matches_store": rec["stem_status"] == ("verified_designated" if store.get_fact(pid, "stem_designation").status == "verified" and store.get_fact(pid, "stem_designation").value["designated"] else rec["stem_status"]),
               "sponsorship_status": rec["sponsorship_status"],
               "sponsorship_store_status": store.get_fact(pid, "sponsorship").status}
        result["programs"].append(row)
        if bad_ids or unsupported_nums or row["verified_claims_without_evidence"] or employment_comparisons:
            result["problems"].append(pid)
    comp = report["metric_comparability"]
    result["metric_comparability"] = [{"metric": m["metric"], "all_comparable": m["all_comparable"],
                                       "comparable_groups": m["comparable_groups"]} for m in comp]
    result["ok"] = not result["problems"]
    (run_dir / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
