"""Minimal gpt-6-luna tool-calling check via Portkey /v1/responses (reasoning kept on).

Harmless local tool (adds two numbers). Two model calls at most. Writes sanitized evidence to
experiments/smoke_test/responses_tools_<stamp>.json. Usage: .venv\\Scripts\\python scripts\\responses_tool_smoke_test.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.core.config import get_settings  # noqa: E402
from backend.app.core.llm import make_client  # noqa: E402

TOOL = {"type": "function", "name": "add_numbers", "description": "Add two numbers.",
        "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                       "required": ["a", "b"], "additionalProperties": False}}


def usage_dict(u):
    if u is None:
        return None
    return {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens, "total_tokens": u.total_tokens,
            "cached_tokens": getattr(u.input_tokens_details, "cached_tokens", None) if u.input_tokens_details else None,
            "reasoning_tokens": getattr(u.output_tokens_details, "reasoning_tokens", None) if u.output_tokens_details else None}


def main() -> int:
    s = get_settings()
    client = make_client(s)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ROOT / "experiments" / "smoke_test" / f"responses_tools_{stamp}.json"
    common = dict(model=s.model, tools=[TOOL], reasoning={"effort": "low"}, store=False,
                  include=["reasoning.encrypted_content"], text={"format": {"type": "json_object"}},
                  max_output_tokens=800)
    instructions = 'Use the add_numbers tool to add 19 and 23, then reply with JSON {"sum": <number>}.'
    record = {"timestamp": stamp, "endpoint": f"{s.portkey_base_url}/responses", "requested_model": s.model,
              "reasoning": {"effort": "low"}, "store": False, "calls": []}
    try:
        t = time.perf_counter()
        r1 = client.responses.create(input=[{"role": "user", "content": instructions}], **common)
        calls = [i for i in r1.output if i.type == "function_call"]
        record["calls"].append({"elapsed_s": round(time.perf_counter() - t, 3), "response_model": r1.model,
                                "output_item_types": [i.type for i in r1.output], "usage": usage_dict(r1.usage)})
        if not calls:
            raise RuntimeError(f"model did not call the tool; output types={[i.type for i in r1.output]}")
        fc = calls[0]
        args = json.loads(fc.arguments)
        result = {"sum": args["a"] + args["b"]}
        follow = [{"role": "user", "content": instructions}] + [i.model_dump(exclude_none=True) for i in r1.output] + [
            {"type": "function_call_output", "call_id": fc.call_id, "output": json.dumps(result)}]
        t = time.perf_counter()
        r2 = client.responses.create(input=follow, **common)
        record["calls"].append({"elapsed_s": round(time.perf_counter() - t, 3), "response_model": r2.model,
                                "output_item_types": [i.type for i in r2.output], "usage": usage_dict(r2.usage)})
        record.update(tool_called=fc.name, tool_args=args, final_text=r2.output_text, ok=json.loads(r2.output_text).get("sum") == 42)
    except Exception as e:
        key = os.getenv("PORTKEY_API_KEY", "")
        msg = str(e).replace(key, "<redacted>") if key else str(e)
        record.update(ok=False, error_type=type(e).__name__, status_code=getattr(e, "status_code", None), error=msg[:1500])
    out.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(record, indent=2))
    return 0 if record.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
