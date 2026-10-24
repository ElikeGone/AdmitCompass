"""One real gpt-6-luna call through Portkey; validates structured output and logs usage.

Usage:  .venv\\Scripts\\python scripts\\smoke_test.py
Uses synthetic text only — no applicant data. Writes sanitized evidence to experiments/smoke_test/.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.core.config import MissingAPIKeyError, get_settings  # noqa: E402
from backend.app.core.llm import structured_call  # noqa: E402
from backend.app.core.usage import append_jsonl  # noqa: E402
from backend.app.schemas.claims import Claim  # noqa: E402

OUT_DIR = ROOT / "experiments" / "smoke_test"


class SmokeResponse(BaseModel):
    status: str = Field(description="Always 'ok'")
    claims: list[Claim] = Field(min_length=2, max_length=3)


SYSTEM = (
    "You are a test fixture for an app that labels claims. Label each statement as "
    "'inference', 'unknown', or 'advice'. Never use 'verified_fact' (no sources are provided). "
    "Leave evidence as an empty list."
)
USER = (
    "Statements: (1) 'Program X may be STEM-designated.' "
    "(2) 'An applicant should confirm STEM status on the official school website.'"
)


def sanitize(msg: str) -> str:
    key = os.getenv("PORTKEY_API_KEY", "")
    return msg.replace(key, "<redacted>") if key else msg


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        settings = get_settings()
    except MissingAPIKeyError as e:
        print(f"FAILED: {e}")
        return 2
    try:
        result, usage = structured_call(SYSTEM, USER, SmokeResponse, label="smoke_test", settings=settings)
    except Exception as e:  # preserve sanitized error for review
        err = {"timestamp": stamp, "model": settings.model, "base_url": settings.portkey_base_url,
               "error_type": type(e).__name__, "status_code": getattr(e, "status_code", None),
               "message": sanitize(str(e))[:2000]}
        (OUT_DIR / f"error_{stamp}.json").write_text(json.dumps(err, indent=2), encoding="utf-8")
        print("FAILED:", json.dumps(err, indent=2))
        return 1
    append_jsonl(usage, OUT_DIR / "usage.jsonl")
    evidence = {"timestamp": stamp, "requested_model": settings.model, "base_url": settings.portkey_base_url,
                "validated_against": "SmokeResponse(claims: list[Claim])", "response": result.model_dump(mode="json"),
                "usage": asdict(usage)}
    (OUT_DIR / f"smoke_{stamp}.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
