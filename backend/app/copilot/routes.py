"""Copilot API.

GET  /api/copilot/status   availability + limits (never the key)
POST /api/copilot/chat     {conversation_id, message, history[], context{program_id, compare_ids, section, run}}

Same-origin only (it spends paid model calls). Rate-limited; history is supplied by the browser and never stored here.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from ..auth.routes import require_same_origin
from ..core.budget import BudgetExceeded
from ..core.config import REPO_ROOT, MissingAPIKeyError
from ..tools.evidence_store import default_store
from .service import CITE, MAX_OUTPUT_TOKENS, CopilotLimiter, answer_question, demo_context, mock_chat, screen_input

router = APIRouter()
limiter = CopilotLimiter()
MAX_MESSAGE = 1000


def mode() -> str:
    return "mock" if os.getenv("AC_COPILOT_MODE", "").lower() == "mock" else "live"


def default_copilot_chat():
    if mode() == "mock":
        return mock_chat
    from ..core.llm import make_portkey_responses_chat
    return make_portkey_responses_chat(max_output_tokens=MAX_OUTPUT_TOKENS, reasoning_effort="low")


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    program_id: str | None = Field(default=None, pattern=r"^[a-z0-9-]{1,80}$")
    compare_ids: list[str] = Field(default_factory=list, max_length=4)
    section: str | None = Field(default=None, max_length=40, pattern=r"^[a-z0-9-]*$")
    run: Literal["demo", "demo-india"] | None = None


class ChatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: str = Field(pattern=r"^[A-Za-z0-9-]{8,64}$")
    message: str = Field(min_length=1, max_length=MAX_MESSAGE)
    history: list[Turn] = Field(default_factory=list, max_length=20)
    context: ChatContext = Field(default_factory=ChatContext)


def _available() -> bool:
    return mode() == "mock" or bool(os.getenv("PORTKEY_API_KEY", "").strip())


@router.get("/api/copilot/status")
def status():
    return {"available": _available(), "mode": mode(), "max_message_chars": MAX_MESSAGE,
            "per_conversation": limiter.per_conv, "per_minute": limiter.per_min, "max_output_tokens": MAX_OUTPUT_TOKENS}


@router.post("/api/copilot/chat")
def chat(body: ChatIn, request: Request):
    require_same_origin(request)
    history = [t.model_dump() for t in body.history]
    reject, refusal = screen_input(body.message, history)
    if reject:
        raise HTTPException(422, reject)
    client = request.client.host if request.client else "unknown"
    over = limiter.check(client, body.conversation_id)
    if over:
        raise HTTPException(429, over)
    base = {"remaining_messages": limiter.remaining(body.conversation_id), "mode": mode()}
    if refusal:
        return {**base, "answer": refusal, "citations": [], "uncertainties": [], "answer_type": "refused", "next_step": None,
                "grounding": {"repaired": False, "fallback": False, "problems": []}, "scope": {}, "usage": {"model_calls": 0}}
    if not _available():
        raise HTTPException(503, "The AI copilot isn't available: no model key is configured on this server. Program pages and the sample analysis still work.")
    store = default_store()
    saved = None
    if body.context.run:
        from ..main import dashboard
        d = dashboard(body.context.run)
        saved = demo_context(d["dashboard"], d["profile"])
    budget = limiter.budget(body.conversation_id)
    try:
        factory = getattr(request.app.state, "copilot_chat_factory", None) or default_copilot_chat
        out = answer_question(store, factory(), message=body.message.strip(), history=history, program_id=body.context.program_id,
                              compare_ids=body.context.compare_ids, saved_analysis=saved, budget=budget)
    except BudgetExceeded as e:
        raise HTTPException(429, f"This conversation reached its model budget ({e}). Start a new conversation.")
    except MissingAPIKeyError:
        raise HTTPException(503, "The AI copilot isn't available: no model key is configured on this server.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "The AI service didn't respond properly. Please try again in a moment.")
    from ..tools.supplementary import by_id
    store_ev = {}
    for c in out["citations"]:
        if c.startswith("sx-"):
            f = by_id(c)
            store_ev[c] = {"program_id": f.program_id, "source_title": f"{f.publisher}" + (" (estimate)" if f.value_kind == "estimate" else ""),
                           "source_url": f.source_url, "excerpt": f.excerpt or f.notes}
        else:
            if c.startswith("lca-"):
                from ..tools.sponsorship import SPONSORSHIP_NOTE, resolve
                x = resolve(c)
                store_ev[c] = {"program_id": None, "source_title": f"U.S. DOL H-1B LCA data FY{x['fiscal_year']} — {x['employer']}",
                               "source_url": x["source_url"], "excerpt": SPONSORSHIP_NOTE}
            else:
                store_ev[c] = store.get_evidence(c)
    out["citations"] = [{"n": i + 1, "evidence_id": c, "program_id": store_ev[c]["program_id"], "source_title": store_ev[c]["source_title"],
                         "source_url": store_ev[c]["source_url"], "excerpt": store_ev[c]["excerpt"][:240]} for i, c in enumerate(out["citations"])]
    num = {c["evidence_id"]: c["n"] for c in out["citations"]}
    out["answer"] = CITE.sub(lambda m: f"[{num[m.group(1)]}]" if m.group(1) in num else "", out["answer"])
    # drop placeholders the model writes instead of a citation, e.g. "[EVIDENCE IDs unavailable for unknown facts]"
    out["answer"] = re.sub(r"\s*\[[^\]]*\b(evidence|citations?|ids?|source ids?)\b[^\]]*\]", "", out["answer"], flags=re.I)
    out["budget"] = budget.snapshot()
    _log_usage(body.conversation_id, out)
    return {**base, **out}


def _log_usage(conversation_id: str, out: dict) -> None:
    """Token usage only (no question/answer text, no ids that identify a person) -> logs/copilot_usage.jsonl (git-ignored)."""
    try:
        p = REPO_ROOT / "logs" / "copilot_usage.jsonl"
        p.parent.mkdir(exist_ok=True)
        u = out.get("usage", {})
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "conversation": conversation_id[:8] + "…", "mode": mode(),
               "model_calls": u.get("model_calls"), "input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens"),
               "reasoning_tokens": u.get("reasoning_tokens"), "seconds": u.get("elapsed_seconds"),
               "fallback": out.get("grounding", {}).get("fallback"), "budget": out.get("budget")}
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except OSError:
        pass
