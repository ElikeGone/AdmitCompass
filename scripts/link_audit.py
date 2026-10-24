"""Audit every URL behind the 30 programs: official program pages and every fact source.

Polite by design: honest User-Agent, 4 concurrent requests, 20 s timeout, 1 retry, no access-control bypass.
Writes experiments/link_audit/link_audit.csv and link_audit_summary.json.
Usage: .venv\\Scripts\\python scripts\\link_audit.py
"""
from __future__ import annotations

import asyncio
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.schemas.discovery import registrable_domain  # noqa: E402

OUT = ROOT / "experiments" / "link_audit"
UA = "AdmitCompassLinkAudit/1.0 (student course project; polite link checker; no scraping)"
BLOCKED = {401, 403, 429, 451}


def targets() -> list[dict]:
    from backend.app.tools.catalog import norm_key
    progs = json.loads((ROOT / "data/programs/programs.json").read_text(encoding="utf-8"))["programs"]
    regs = json.loads((ROOT / "data/sources/source_registry.json").read_text(encoding="utf-8"))["sources"]
    disc = json.loads((ROOT / "data/discovery/discovered_programs.json").read_text(encoding="utf-8"))["programs"]
    used = {e["source_id"] for p in progs for e in p["evidence"]}
    uni_by_pid = {p["program_id"]: p["university"] for p in progs}
    raw_dir = ROOT / "data/sources/raw/enrich"
    for f in raw_dir.glob("batch*.json") if raw_dir.exists() else []:
        for r in json.loads(f.read_text(encoding="utf-8"))["programs"]:
            uni_by_pid.setdefault(r["program_id"], r["university"])
    rows, seen = [], set()
    for s in regs:
        pid = re.sub(r"^src-|-\d+$", "", s["source_id"])
        if (pid, s["url"]) in seen:
            continue
        seen.add((pid, s["url"]))
        rows.append({"program_id": pid, "program_key": norm_key(uni_by_pid.get(pid, pid)), "tier": "evidence",
                     "role": "fact_source" if s["source_id"] in used else "checked_not_used", "url": s["url"], "recorded_accessed": s["accessed"]})
    for d in disc:
        rows.append({"program_id": d["discovery_id"], "program_key": norm_key(d["university"]), "tier": "discovered",
                     "role": "official_program_page", "url": d["provenance_url"], "recorded_accessed": d["fetched"]})
    return rows


def program_match(text: str) -> bool:
    t = text.lower()
    return "mba" in t or "master of business administration" in t


async def check(client: httpx.AsyncClient, sem: asyncio.Semaphore, row: dict) -> dict:
    url = row["url"]
    is_pdf = url.lower().endswith(".pdf")
    out = {**row, "status": "", "http_status": "", "final_url": "", "redirected": False, "same_site": "", "mba_mentioned": "", "issue": "", "resolution": ""}
    async with sem:
        for attempt in (1, 2):
            try:
                r = await client.get(url, follow_redirects=True)
                final = str(r.url)
                out.update(http_status=r.status_code, final_url=final, redirected=final.rstrip("/") != url.rstrip("/"),
                           same_site=registrable_domain(final) == registrable_domain(url))
                if r.status_code in BLOCKED:
                    out.update(status="blocked", issue=f"HTTP {r.status_code} (site refused automated access)",
                               resolution="Keep official URL; open in a browser. No bypass attempted.")
                elif r.status_code in (404, 410):
                    out.update(status="broken", issue=f"HTTP {r.status_code}", resolution="Not used as evidence; needs a confirmed replacement")
                elif r.status_code >= 400:
                    out.update(status="error", issue=f"HTTP {r.status_code}", resolution="Retry later")
                else:
                    body = "" if is_pdf else r.text[:200000]
                    out["mba_mentioned"] = True if is_pdf else program_match(body)
                    if not out["same_site"]:
                        out.update(status="redirect_offsite", issue=f"Redirects to {urlparse(final).hostname}", resolution="Review destination")
                    elif out["redirected"]:
                        out.update(status="redirect_ok", issue="Redirects within the official site", resolution="Use final URL for display")
                    else:
                        out.update(status="ok", resolution="No change")
                    if out["mba_mentioned"] is False:
                        out["issue"] = (out["issue"] + "; " if out["issue"] else "") + "page text does not mention MBA (may be JS-rendered)"
                return out
            except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadError) as e:
                if attempt == 2:
                    msg = str(e) or type(e).__name__
                    tls = "certificate" in msg.lower() or "ssl" in msg.lower()
                    out.update(status="unreachable", issue=("TLS/certificate error" if tls else type(e).__name__) + f": {msg[:120]}",
                               resolution="Keep official URL; open in a browser")
                await asyncio.sleep(1.5)
    return out


async def main() -> int:
    rows = targets()
    sem = asyncio.Semaphore(4)
    async with httpx.AsyncClient(headers={"User-Agent": UA, "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.5"},
                                 timeout=httpx.Timeout(20.0), max_redirects=8) as client:
        results = await asyncio.gather(*(check(client, sem, r) for r in rows))
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    OUT.mkdir(parents=True, exist_ok=True)
    cols = ["program_id", "tier", "role", "status", "http_status", "checked_at", "original_url", "final_url", "redirected", "same_site",
            "mba_mentioned", "recorded_accessed", "issue", "resolution"]
    with (OUT / "link_audit.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in sorted(results, key=lambda x: (x["program_id"], x["role"], x["url"])):
            w.writerow({**{k: r.get(k, "") for k in cols}, "checked_at": checked_at, "original_url": r["url"]})
    by = lambda key: {k: sum(1 for r in results if r[key] == k) for k in sorted({r[key] for r in results})}  # noqa: E731
    prog_ids = {r["program_key"] for r in results}
    official = [r for r in results if r["role"] in ("official_program_page", "fact_source")]
    summary = {"checked_at": checked_at, "programs_covered": len(prog_ids), "urls_checked": len(results), "by_status": by("status"),
               "by_role": by("role"), "fact_sources_and_program_pages": {"checked": len(official), "by_status": {k: sum(1 for r in official if r["status"] == k) for k in sorted({r["status"] for r in official})}},
               "method": {"user_agent": UA, "concurrency": 4, "timeout_s": 20, "retries": 1, "bypass": "none"}}
    (OUT / "link_audit_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    # Compact per-URL status for the app (no page content stored).
    status = {r["url"]: {"status": r["status"], "http_status": r["http_status"], "final_url": r["final_url"] or r["url"],
                         "checked_at": checked_at} for r in results}
    (ROOT / "data" / "links").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "links" / "link_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
