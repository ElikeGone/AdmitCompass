"""Portkey client for gpt-6-luna (OpenAI-compatible API).

Config mirrors the working course setup in hw3/agent.py: OpenAI SDK, base_url
https://api.portkey.ai/v1, headers x-portkey-api-key and x-portkey-provider.
"""
from __future__ import annotations

import json
import os
import time
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from .config import Settings, get_settings
from .usage import UsageRecord, record_from_usage

T = TypeVar("T", bound=BaseModel)


def make_client(settings: Settings) -> OpenAI:
    headers = {
        "x-portkey-api-key": settings.portkey_api_key,
        "x-portkey-provider": settings.portkey_provider,
    }
    # Portkey docs: "x-portkey-cache-force-refresh: true" bypasses any gateway cache hit, so measured tokens are
    # fresh calls, not replays (earlier runs showed likely cache replays). On by default; set to 0 to allow cache.
    if os.getenv("PORTKEY_CACHE_FORCE_REFRESH", "1") != "0":
        headers["x-portkey-cache-force-refresh"] = "true"
    return OpenAI(
        api_key=settings.portkey_api_key,
        base_url=settings.portkey_base_url,
        default_headers=headers,
        max_retries=1,
        timeout=60,
    )


def structured_call(system: str, user: str, schema: type[T], *, label: str = "",
                    settings: Settings | None = None, max_output_tokens: int = 800) -> tuple[T, UsageRecord]:
    """One chat completion in JSON mode, validated against `schema`."""
    settings = settings or get_settings()
    client = make_client(settings)
    schema_json = json.dumps(schema.model_json_schema())
    started = time.perf_counter()
    resp = client.chat.completions.create(
        model=settings.model,
        messages=[
            {"role": "system", "content": f"{system}\nReturn only JSON matching this JSON Schema:\n{schema_json}"},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        max_completion_tokens=max_output_tokens,
    )
    elapsed = time.perf_counter() - started
    usage = record_from_usage(resp.model or settings.model, resp.usage, elapsed, label=label)
    parsed = schema.model_validate_json(resp.choices[0].message.content or "")
    return parsed, usage


# ---------- multi-turn chat with tools (used by agents) ----------
from dataclasses import dataclass, field  # noqa: E402
from typing import Any, Callable  # noqa: E402


@dataclass
class ChatResult:
    content: str | None
    tool_calls: list[dict] = field(default_factory=list)  # [{"id", "name", "arguments"}]
    usage: UsageRecord | None = None
    assistant_message: dict[str, Any] = field(default_factory=dict)


ChatFn = Callable[..., ChatResult]  # chat(messages, tools, label, tool_choice="auto"|"none")


def make_portkey_chat(settings: Settings | None = None, max_output_tokens: int = 3000) -> ChatFn:
    """Return a chat function bound to gpt-6-luna via Portkey (JSON mode, optional tools)."""
    settings = settings or get_settings()
    client = make_client(settings)

    def chat(messages: list[dict], tools: list[dict] | None, label: str, tool_choice: str = "auto") -> ChatResult:
        kwargs: dict[str, Any] = dict(model=settings.model, messages=messages,
                                      response_format={"type": "json_object"},
                                      max_completion_tokens=max_output_tokens)
        if tools:
            kwargs.update(tools=tools, tool_choice=tool_choice)
        started = time.perf_counter()
        resp = client.chat.completions.create(**kwargs)
        usage = record_from_usage(settings.model, resp.usage, time.perf_counter() - started, label=label)
        msg = resp.choices[0].message
        calls = [{"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments}
                 for tc in (msg.tool_calls or [])]
        assistant = {"role": "assistant", "content": msg.content or ""}
        if calls:
            assistant["tool_calls"] = [{"id": c["id"], "type": "function",
                                        "function": {"name": c["name"], "arguments": c["arguments"]}} for c in calls]
        return ChatResult(content=msg.content, tool_calls=calls, usage=usage, assistant_message=assistant)

    chat.model = settings.model  # type: ignore[attr-defined]
    return chat


# ---------- Responses API adapter (used by agents; supports tools + reasoning on gpt-6-luna) ----------
def _to_responses_input(messages: list[dict]) -> tuple[str, list[dict]]:
    """Convert the runner's neutral message list to (instructions, Responses input items)."""
    instructions, items = [], []
    for m in messages:
        if "_responses_items" in m:              # opaque output items from a previous turn (incl. reasoning)
            items.extend(m["_responses_items"])
        elif m.get("role") == "system":
            instructions.append(m["content"])
        elif m.get("role") == "tool":
            items.append({"type": "function_call_output", "call_id": m["tool_call_id"], "output": m["content"]})
        elif m.get("role") in ("user", "assistant"):
            items.append({"role": m["role"], "content": m.get("content") or ""})
    # JSON mode requires the word "json" in the input messages (not only in instructions).
    if not any("json" in str(i.get("content", "")).lower() for i in items if "role" in i):
        items.insert(0, {"role": "user", "content": "Respond with a JSON object."})
    return "\n\n".join(instructions), items


def _to_responses_tools(tools: list[dict] | None) -> list[dict] | None:
    if not tools:
        return None
    return [{"type": "function", "name": t["function"]["name"], "description": t["function"].get("description", ""),
             "parameters": t["function"]["parameters"]} for t in tools]


def make_portkey_responses_chat(settings: Settings | None = None, max_output_tokens: int = 4000,
                                reasoning_effort: str | None = None) -> ChatFn:
    """gpt-6-luna via Portkey /v1/responses. Stateless (store=False); encrypted reasoning items are passed back."""
    import os
    settings = settings or get_settings()
    client = make_client(settings)
    effort = reasoning_effort or os.getenv("ADMITCOMPASS_REASONING_EFFORT", "low")

    def chat(messages: list[dict], tools: list[dict] | None, label: str, tool_choice: str = "auto") -> ChatResult:
        instructions, items = _to_responses_input(messages)
        kwargs: dict[str, Any] = dict(model=settings.model, instructions=instructions, input=items,
                                      reasoning={"effort": effort}, store=False,
                                      include=["reasoning.encrypted_content"],
                                      text={"format": {"type": "json_object"}}, max_output_tokens=max_output_tokens)
        rtools = _to_responses_tools(tools)
        if rtools:
            kwargs.update(tools=rtools, tool_choice=tool_choice)
        started = time.perf_counter()
        resp = client.responses.create(**kwargs)
        usage = record_from_usage(settings.model, resp.usage, time.perf_counter() - started, label=label)
        out_items = [i.model_dump(exclude_none=True) for i in resp.output]
        calls = [{"id": i.call_id, "name": i.name, "arguments": i.arguments} for i in resp.output if i.type == "function_call"]
        return ChatResult(content=resp.output_text if not calls else None, tool_calls=calls, usage=usage,
                          assistant_message={"_responses_items": out_items})

    chat.model = settings.model  # type: ignore[attr-defined]
    chat.reasoning_effort = effort  # type: ignore[attr-defined]
    return chat
