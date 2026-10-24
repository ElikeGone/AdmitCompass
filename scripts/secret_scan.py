"""Scan every file git would commit (tracked + untracked-not-ignored) for anything resembling a credential.

    .venv\\Scripts\\python scripts\\secret_scan.py

Prints only file, line number, rule and a MASKED snippet; never prints a full matching value. Exit code 1 if anything
looks like a real secret. Known fake test values are listed explicitly in ALLOW.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    "openai/portkey-style key": re.compile(r"\b(sk|pk)-[A-Za-z0-9_\-]{16,}"),
    "key assignment": re.compile(r"(?i)\b(PORTKEY_API_KEY|OPENAI_API_KEY|API_KEY|SECRET|TOKEN|PASSWORD)\s*[=:]\s*['\"]?([A-Za-z0-9_\-+/=]{12,})"),
    "bearer token": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}"),
    "aws access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "slack token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "x-portkey-api-key value": re.compile(r"(?i)x-portkey-api-key['\"]?\s*[:=]\s*['\"]([A-Za-z0-9_\-+/=]{12,})"),
}
# Deliberately fake values used by tests/scripts (verified by reading each occurrence).
ALLOW = {"sk-redteam-secret-123456", "sk-redteam-secret-654321", "parent-test-value", "repo-test-value", "preset-test-value", "fresh-clone-placeholder-not-a-real-key", "test-not-a-real-key",
         "your-portkey-key-here", "your-course-key", "settings.portkey_api_key"}


def files() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True).stdout
    return [ROOT / f for f in out.splitlines() if f.strip()]


def mask(s: str) -> str:
    return s[:6] + "…" + f"({len(s)} chars)" if len(s) > 8 else "…"


hits, scanned = [], 0
for f in files():
    try:
        text = f.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue   # binary (images, fonts, zip) — see note in the report
    scanned += 1
    for i, line in enumerate(text.splitlines(), 1):
        for rule, pat in RULES.items():
            for m in pat.finditer(line):
                val = m.group(m.lastindex or 0)
                if any(a in line for a in ALLOW) or val.lower() in {"none", "null", "true", "false"} or re.fullmatch(r"[A-Z_]+", val):
                    continue
                if rule == "key assignment" and re.search(r"os\.getenv|environ|settings\.|\{|getattr", line):
                    continue
                hits.append((f.relative_to(ROOT).as_posix(), i, rule, mask(val)))
print(f"Scanned {scanned} text files that git would commit.")
for h in hits:
    print("POSSIBLE SECRET:", *h)
print("Result:", "CLEAN — nothing resembling a real credential." if not hits else f"{len(hits)} item(s) need review.")
sys.exit(1 if hits else 0)
