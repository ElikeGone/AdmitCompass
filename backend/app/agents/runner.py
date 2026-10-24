"""Generic bounded agent runner: tool loop -> JSON -> Pydantic validation -> (optional) one corrective retry."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, TypeVar

from pydantic import BaseModel, ValidationError

from ..core.budget import RunBudget
from ..core.llm import ChatFn
from ..core.usage import UsageRecord
from ..tools.agent_tools import ToolBox

T = TypeVar("T", bound=BaseModel)

MAX_TOOL_ROUNDS = 4       # model turns that may request tools before it must answer
MAX_ATTEMPTS = 2          # initial + one corrective retry for invalid JSON/schema


class AgentFailure(RuntimeError):
    pass


@dataclass
class AgentResult:
    output: BaseModel
    usages: list[UsageRecord] = field(default_factory=list)
    attempts: int = 1


def run_agent(*, agent: str, system: str, user_payload: dict, schema: type[T], tool_names: tuple[str, ...],
              chat: ChatFn, toolbox: ToolBox, budget: RunBudget, event: Callable[..., None],
              extra_feedback: str | None = None, downgrade_unsupported_verified: bool = False) -> AgentResult:
    schema_hint = json.dumps(schema.model_json_schema())
    messages = [
        {"role": "system", "content": f"{system}\n\nWhen finished, reply with ONLY a JSON object matching this JSON Schema:\n{schema_hint}"},
        {"role": "user", "content": json.dumps(user_payload, default=str)},
    ]
    if extra_feedback:
        messages.append({"role": "user", "content": extra_feedback})
    tools = toolbox.specs(tool_names) if tool_names else None
    usages: list[UsageRecord] = []
    rounds = 0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        while True:
            budget.check_request()
            allow_tools = bool(tools) and rounds < MAX_TOOL_ROUNDS
            # After the round limit, tools stay declared (history references them) but calls are disabled.
            res = chat(messages, tools, agent, "auto" if allow_tools else "none")
            budget.record_request(res.usage.total_tokens if res.usage else None)
            if res.usage:
                usages.append(res.usage)
            event("llm_call", agent, {"attempt": attempt, "round": rounds, "tool_calls_requested": len(res.tool_calls),
                                      "input_tokens": res.usage.input_tokens if res.usage else None,
                                      "cached_input_tokens": res.usage.cached_input_tokens if res.usage else None,
                                      "output_tokens": res.usage.output_tokens if res.usage else None,
                                      "reasoning_tokens": res.usage.reasoning_tokens if res.usage else None,
                                      "elapsed_seconds": res.usage.elapsed_seconds if res.usage else None})
            if res.tool_calls and allow_tools:
                rounds += 1
                messages.append(res.assistant_message)
                for tc in res.tool_calls:
                    messages.append({"role": "tool", "tool_call_id": tc["id"],
                                     "content": toolbox.call(agent, tc["name"], tc["arguments"])})
                continue
            break
        content = res.content or ""
        try:
            downgraded = 0
            if downgrade_unsupported_verified:
                obj = json.loads(content)
                downgraded = _downgrade_evidence_less_verified(obj)
                parsed = schema.model_validate(obj)
            else:
                parsed = schema.model_validate_json(content)
            event("validation", agent, {"attempt": attempt, "ok": True, "downgraded_verified_claims": downgraded})
            return AgentResult(output=parsed, usages=usages, attempts=attempt)
        except (ValidationError, ValueError, TypeError) as e:
            err = str(e)[:800]
            event("validation", agent, {"attempt": attempt, "ok": False, "error": err[:300]})
            if attempt == MAX_ATTEMPTS:
                raise AgentFailure(f"{agent}: output failed validation after {MAX_ATTEMPTS} attempts: {err[:300]}") from e
            messages.append({"role": "assistant", "content": content[:4000]})
            messages.append({"role": "user", "content": f"Your JSON was invalid: {err}\nReturn corrected JSON only."})
    raise AgentFailure(f"{agent}: no output")  # pragma: no cover


def _downgrade_evidence_less_verified(obj) -> int:
    """Relabel 'verified_fact' claims that cite no evidence as 'inference' (weakens the claim, never the checks)."""
    n = 0
    if isinstance(obj, dict):
        if obj.get("label") == "verified_fact" and "text" in obj and not obj.get("evidence") and not obj.get("evidence_ids"):
            obj["label"] = "inference"
            n += 1
        for v in obj.values():
            n += _downgrade_evidence_less_verified(v)
    elif isinstance(obj, list):
        for v in obj:
            n += _downgrade_evidence_less_verified(v)
    return n
