"""Deterministic ingestion + independent validation of supplementary facts -> data/programs/supplementary.json

For every raw record (data/sources/raw/supp/*.json) this script itself re-fetches the source page (honest user agent,
robots.txt honored incl. crawl-delay, one fetch per URL, no bypassing) and checks:
  - identity: official records must come from the program's official domain; secondary rows must contain the school label
  - value: the number/date/text must appear in the raw page text (secondary: in the same table row as the school)
Only records that pass become status "verified". Blocked pages stay "blocked"; mismatches stay "unverified".
Raw collector records (including model-assisted research) are never trusted on their own.

    .venv\\Scripts\\python scripts\\build_supplementary.py [--offline]   # --offline reuses the cached page snapshots
"""
from __future__ import annotations

import hashlib
import html as htmllib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.schemas.supplementary import SuppFact  # noqa: E402

RAW = ROOT / "data" / "sources" / "raw" / "supp"
CACHE = ROOT / "data" / "sources" / "cache" / "supp"
OUT = ROOT / "data" / "programs" / "supplementary.json"
REPORT = ROOT / "experiments" / "research" / "supplementary_validation.csv"
UA = "AdmitCompass-research/1.0 (MGT 409 course project; polite, one fetch per page)"
CRAWL_DELAY = {"poetsandquants.com": 10.0}
DEFAULT_DELAY = 2.0
NEAR = {"class_size": r"class|students|enroll|size|cohort", "class_median_gmat": r"gmat", "class_avg_gmat": r"gmat",
        "class_pct_international": r"international|foreign|citizen|countr", "mandatory_fees": r"fee",
        "cost_of_attendance": r"total|budget|cost|attendance", "tuition": r"tuition"}
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]


def official_domains() -> dict[str, str]:
    progs = json.loads((ROOT / "data" / "programs" / "programs.json").read_text(encoding="utf-8"))
    srcs = {s["source_id"]: s for s in json.loads((ROOT / "data" / "sources" / "source_registry.json").read_text(encoding="utf-8"))["sources"]}
    out = {}
    for p in progs["programs"]:
        hosts = {urlparse(srcs[e["source_id"]]["url"]).hostname for e in p.get("evidence", []) if e["source_id"] in srcs}
        out[p["program_id"]] = {".".join(h.split(".")[-2:]) for h in hosts if h}
    return out


def robots_allows(url: str, client: httpx.Client) -> bool:
    """Minimal reader of the `User-agent: *` group (Python's robotparser misreads some multi-group files)."""
    host = urlparse(url)
    try:
        txt = client.get(f"{host.scheme}://{host.netloc}/robots.txt", timeout=15).text
    except httpx.HTTPError:
        return True
    rules, active = [], False
    for line in txt.splitlines():
        line = line.split("#")[0].strip()
        if not line or ":" not in line:
            continue
        k, v = (x.strip() for x in line.split(":", 1))
        if k.lower() == "user-agent":
            active = v == "*"
        elif active and k.lower() in ("allow", "disallow"):
            rules.append((k.lower(), v))
    best = ("allow", "")
    for kind, path in rules:
        if path and host.path.startswith(path) and len(path) >= len(best[1]):
            best = (kind, path)
    return best[0] == "allow"


def page_text(raw_html: str) -> tuple[str, list[str]]:
    rows = [re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", r))) for r in re.split(r"</tr>", raw_html, flags=re.I)]
    text = re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", raw_html, flags=re.S | re.I)))
    return text, rows


def fetch(url: str, client: httpx.Client, last: dict, offline: bool) -> tuple[str | None, str]:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (hashlib.sha256(url.encode()).hexdigest()[:24] + ".html")
    if offline:
        return (f.read_text(encoding="utf-8"), "cached") if f.exists() else (None, "no cached copy")
    host = urlparse(url).hostname or ""
    if not robots_allows(url, client):
        return None, "disallowed by robots.txt"
    wait = CRAWL_DELAY.get(".".join(host.split(".")[-2:]), DEFAULT_DELAY) - (time.time() - last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    try:
        r = client.get(url, timeout=25, follow_redirects=True)
    except httpx.HTTPError as e:
        return None, f"unreachable ({type(e).__name__})"
    finally:
        last[host] = time.time()
    if r.status_code in (401, 403, 429):
        return None, f"blocked (HTTP {r.status_code})"
    if r.status_code >= 400:
        return None, f"HTTP {r.status_code}"
    body = r.text
    if "pdf" in r.headers.get("content-type", "").lower() or r.content[:5] == b"%PDF-":
        import io
        from pypdf import PdfReader   # dev-only dependency
        body = "<pdf>" + "\n".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(r.content)).pages) + "</pdf>"
    f.write_text(body, encoding="utf-8")
    return body, f"HTTP {r.status_code}"


def number_forms(v: float, printed: str | None) -> list[str]:
    if printed:
        return [printed]
    i = int(v) if float(v).is_integer() else v
    return [f"{i:,}", str(i)] if isinstance(i, int) else [str(v)]


def date_found(iso: str, text: str) -> bool:
    y, m, d = (int(x) for x in iso.split("-"))
    mon = MONTHS[m - 1]
    pat = rf"\b({mon}|{mon[:3]}\.?|{mon[:4]}\.?)\s+0?{d}(st|nd|rd|th)?\b"
    return bool(re.search(pat, text, re.I)) or f"{m}/{d}/{y}" in text or iso in text


RAW_HTML: dict[str, str] = {}


def raw_html_of(rec: dict) -> str | None:
    return RAW_HTML.get(rec.get("source_url", ""))


def check(rec: dict, text: str, rows: list[str], domains: dict) -> tuple[bool, str]:
    pid, field, v = rec["program_id"], rec["field"], rec.get("value")
    if rec["source_type"] == "official":
        host = ".".join((urlparse(rec["source_url"]).hostname or "").split(".")[-2:])
        if domains.get(pid) and host not in domains[pid]:
            return False, f"source host {host} is not the program's official domain {sorted(domains[pid])}"
    if rec["source_type"] == "secondary":
        label = rec["row_label"]
        hit = [r for r in rows if label.lower() in r.lower() and rec["printed"] in r]
        return (bool(hit), f"row with '{label}' and '{rec['printed']}'" + ("" if hit else " NOT found"))
    if field == "application_deadlines":
        missing = [x["deadline"] for x in v if not date_found(x["deadline"], text)]
        return (not missing, "all deadline dates found on page" if not missing else f"dates not found: {missing}")
    if field == "hiring_employers":
        # every name must appear on the page (visible text, or image alt text for logo walls)
        hay = (text + " " + htmllib.unescape(" ".join(re.findall(r'alt="([^"]*)"', raw_html_of(rec) or "", re.I)))).lower()
        hay = re.sub(r"\s+", " ", hay)
        names = rec.get("printed_values") or v
        missing = [n for n in names if re.sub(r"\s+", " ", n.lower()) not in hay]
        return (not missing, f"all {len(names)} employer names found on page" if not missing else f"names NOT found: {missing[:5]}")
    if field == "scholarships":
        words = re.findall(r"[a-z]{4,}", (rec.get("excerpt") or str(v)).lower())
        windows = [" ".join(words[i:i + 5]) for i in range(0, max(1, len(words) - 4))]
        norm = " ".join(re.findall(r"[a-z]{4,}", text.lower()))
        ok = any(w and w in norm for w in windows)
        return ok, "excerpt wording found on page" if ok else "excerpt wording NOT found on page"
    forms = number_forms(float(v), None)
    if field == "class_pct_international":
        pats = [rf"\b{re.escape(f)}\s*%" for f in forms]
    else:
        pats = [rf"(?<![\d,.]){re.escape(f)}(?![\d,])" for f in forms]
    # the number must sit near a word that says what it is (a bare "367" elsewhere on the page doesn't count)
    near = NEAR.get(field)
    for p in pats:
        for m in re.finditer(p, text):
            window = text[max(0, m.start() - 120):m.end() + 120]
            if near is None or re.search(near, window, re.I):
                return True, f"value {forms[0]} found on page near '{near or 'any'}'"
    return False, f"value {forms[0]} NOT found on page" + (f" near '{near}'" if near else "")


def main(offline: bool = False) -> None:
    domains = official_domains()
    records = []
    for f in sorted(RAW.glob("*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            r["_file"] = f.name
            r.setdefault("source_type", "official")
            r.setdefault("value_kind", "published")
            records.append(r)
    pages: dict[str, tuple[str | None, str]] = {}
    last: dict[str, float] = {}
    out, report = [], []
    with httpx.Client(headers={"User-Agent": UA}) as client:
        for r in records:
            fid = f"sx-{r['program_id']}-{r['field'].replace('_', '-')}-{re.sub(r'[^a-z]', '', r['publisher'].lower())[:12]}"
            status_in = r.get("status", "found")
            if status_in in ("not_found", "blocked") or r.get("value") in (None, ""):
                status, why = ("blocked" if status_in == "blocked" else "not_found"), f"collector reported {status_in}"
            else:
                if r["source_url"] not in pages:
                    pages[r["source_url"]] = fetch(r["source_url"], client, last, offline)
                raw, fetch_note = pages[r["source_url"]]
                if raw is None:
                    status, why = ("blocked" if "blocked" in fetch_note or "robots" in fetch_note else "unverified"), fetch_note
                else:
                    RAW_HTML[r["source_url"]] = raw
                    text, rows = page_text(raw)
                    ok, why = check(r, text, rows, domains)
                    status = "verified" if ok else "unverified"
            rec = {"fact_id": fid, "program_id": r["program_id"], "field": r["field"], "value": r.get("value"), "unit": r.get("unit", "text"),
                   "period": r.get("period"), "period_basis": r.get("period_basis", "annual"), "source_url": r["source_url"],
                   "publisher": r.get("publisher", ""), "source_type": r.get("source_type", "official"),
                   "value_kind": r.get("value_kind", "published"), "retrieved_on": r.get("retrieved_on", ""), "status": status,
                   "validation": why[:200], "excerpt": (r.get("excerpt") or "")[:300], "notes": (r.get("notes") or "")[:300]}
            if rec["status"] != "verified":
                rec["value"] = rec["value"] if rec["status"] == "unverified" else None
            SuppFact.model_validate(rec)
            out.append(rec)
            report.append([r["_file"], fid, r["program_id"], r["field"], rec["source_type"], rec["value_kind"], status, why[:120]])
    # dedupe ids (keep the first verified)
    seen, final = {}, []
    for rec in out:
        k = rec["fact_id"]
        if k in seen and (seen[k]["status"] == "verified" or rec["status"] != "verified"):
            continue
        if k in seen:
            final.remove(seen[k])
        seen[k] = rec
        final.append(rec)
    OUT.write_text(json.dumps({"generated_on": time.strftime("%Y-%m-%d"), "facts": final}, indent=1), encoding="utf-8")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    import csv
    with REPORT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["raw_file", "fact_id", "program_id", "field", "source_type", "value_kind", "status", "validation"]); w.writerows(report)
    from collections import Counter
    print(Counter((x["source_type"], x["status"]) for x in final))


if __name__ == "__main__":
    main(offline="--offline" in sys.argv)
