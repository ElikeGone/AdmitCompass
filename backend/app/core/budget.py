"""Per-run spending guard: caps model requests, total tokens, and tool calls."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class RunBudget:
    max_requests: int = field(default_factory=lambda: int(os.getenv("ADMITCOMPASS_MAX_REQUESTS_PER_RUN", "20")))
    max_total_tokens: int = field(default_factory=lambda: int(os.getenv("ADMITCOMPASS_MAX_TOKENS_PER_RUN", "200000")))
    max_tool_calls: int = field(default_factory=lambda: int(os.getenv("ADMITCOMPASS_MAX_TOOL_CALLS_PER_RUN", "40")))
    max_seconds: float = field(default_factory=lambda: float(os.getenv("ADMITCOMPASS_MAX_SECONDS_PER_RUN", "300")))
    requests: int = 0
    total_tokens: int = 0
    tool_calls: int = 0
    started_at: float = field(default_factory=time.monotonic)

    def check_request(self) -> None:
        """Call before each model request; raises if the next request would exceed the budget."""
        if self.requests >= self.max_requests:
            raise BudgetExceeded(f"request limit reached ({self.requests}/{self.max_requests})")
        if self.total_tokens >= self.max_total_tokens:
            raise BudgetExceeded(f"token limit reached ({self.total_tokens}/{self.max_total_tokens})")
        elapsed = time.monotonic() - self.started_at
        if elapsed >= self.max_seconds:
            raise BudgetExceeded(f"time limit reached ({elapsed:.0f}s/{self.max_seconds:.0f}s)")

    def record_request(self, tokens: int | None) -> None:
        self.requests += 1
        self.total_tokens += tokens or 0

    def check_tool(self) -> None:
        if self.tool_calls >= self.max_tool_calls:
            raise BudgetExceeded(f"tool-call limit reached ({self.tool_calls}/{self.max_tool_calls})")
        self.tool_calls += 1

    def snapshot(self) -> dict:
        return {"requests": self.requests, "max_requests": self.max_requests, "total_tokens": self.total_tokens,
                "max_total_tokens": self.max_total_tokens, "tool_calls": self.tool_calls,
                "max_tool_calls": self.max_tool_calls, "max_seconds": self.max_seconds}
