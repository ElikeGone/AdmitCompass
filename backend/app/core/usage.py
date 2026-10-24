"""Token usage logging. Records only what the API reports; missing values stay None ("unknown").

Never records API keys, prompts, or applicant data — only metadata about the call.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# USD per 1M tokens. Empty until a documented price for gpt-6-luna is confirmed;
# add {"input": x, "cached_input": y, "output": z, "source": url} when known.
PRICES_PER_MTOK: dict[str, dict[str, Any]] = {}


@dataclass
class UsageRecord:
    model: str
    timestamp: str
    elapsed_seconds: float
    input_tokens: int | None
    cached_input_tokens: int | None
    output_tokens: int | None
    reasoning_tokens: int | None
    total_tokens: int | None
    estimated_cost_usd: float | None
    cost_basis: str
    label: str = ""


def _get(obj: Any, name: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _first(*vals: Any) -> Any:
    return next((v for v in vals if v is not None), None)


def estimate_cost(model: str, input_tokens: int | None, cached: int | None, output: int | None) -> tuple[float | None, str]:
    price = PRICES_PER_MTOK.get(model)
    if price is None:
        return None, "unknown: no documented price configured"
    if input_tokens is None or output is None:
        return None, "unknown: token counts not reported"
    cached_n = cached or 0
    cost = ((input_tokens - cached_n) * price["input"] + cached_n * price.get("cached_input", price["input"])
            + output * price["output"]) / 1_000_000
    return round(cost, 8), f"documented price: {price.get('source', 'unspecified')}"


def record_from_usage(model: str, usage: Any, elapsed_seconds: float, label: str = "") -> UsageRecord:
    # Chat Completions names first, then Responses API names.
    input_tokens = _first(_get(usage, "prompt_tokens"), _get(usage, "input_tokens"))
    output_tokens = _first(_get(usage, "completion_tokens"), _get(usage, "output_tokens"))  # includes reasoning
    total = _get(usage, "total_tokens")
    in_details = _first(_get(usage, "prompt_tokens_details"), _get(usage, "input_tokens_details"))
    out_details = _first(_get(usage, "completion_tokens_details"), _get(usage, "output_tokens_details"))
    cached = _get(in_details, "cached_tokens")  # None if not explicitly reported
    reasoning = _get(out_details, "reasoning_tokens")
    cost, basis = estimate_cost(model, input_tokens, cached, output_tokens)
    return UsageRecord(
        model=model,
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        elapsed_seconds=round(elapsed_seconds, 3),
        input_tokens=input_tokens,
        cached_input_tokens=cached,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning,
        total_tokens=total,
        estimated_cost_usd=cost,
        cost_basis=basis,
        label=label,
    )


def append_jsonl(record: UsageRecord, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record)) + "\n")
