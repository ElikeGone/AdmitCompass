"""In-memory run manager for a local single-user demo.

- Run ids are generated server-side.
- At most one live analysis at a time and a capped number per server process (paid-call protection).
- Each run executes in a background thread; the UI polls events from the orchestrator's real trace.
- Profiles submitted through the UI live in memory only and are never written to disk.
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from .core.budget import RunBudget
from .core.config import redact_secrets as redact
from .core.llm import ChatFn
from .orchestrator import Orchestrator
from .schemas.applicant import ApplicantProfile
from .tools.evidence_store import EvidenceStore


class RunRejected(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code, self.message = status_code, message


@dataclass
class RunState:
    run_id: str
    profile: ApplicantProfile
    status: str = "running"   # running | completed | completed_with_violations | stopped_budget | failed_closed
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    orchestrator: Orchestrator | None = None
    report: Any = None
    error: str | None = None


def max_live_runs() -> int:
    return int(os.getenv("ADMITCOMPASS_MAX_LIVE_RUNS_PER_SERVER", "3"))


class RunManager:
    def __init__(self, chat_factory: Callable[[], ChatFn], store_factory: Callable[[], EvidenceStore]):
        self._chat_factory, self._store_factory = chat_factory, store_factory
        self._lock = threading.Lock()
        self.runs: dict[str, RunState] = {}
        self.live_runs_started = 0

    def active(self) -> RunState | None:
        return next((r for r in self.runs.values() if r.status == "running"), None)

    def start(self, profile: ApplicantProfile) -> RunState:
        with self._lock:
            if self.active():
                raise RunRejected(409, "An analysis is already running. Wait for it to finish.")
            if self.live_runs_started >= max_live_runs():
                raise RunRejected(429, f"This server allows {max_live_runs()} live analyses per session to protect "
                                       "the course API budget. Restart the server to reset.")
            chat = self._chat_factory()  # may raise MissingAPIKeyError before anything is spent
            run_id = uuid.uuid4().hex[:12]
            from .tools.catalog import store_for_profile
            orch = Orchestrator(chat, store_for_profile(self._store_factory(), profile), budget=RunBudget(),
                                model=getattr(chat, "model", "gpt-6-luna"))
            state = RunState(run_id=run_id, profile=profile, orchestrator=orch)
            self.runs[run_id] = state
            self.live_runs_started += 1
        threading.Thread(target=self._execute, args=(state,), daemon=True, name=f"run-{run_id}").start()
        return state

    def _execute(self, state: RunState) -> None:
        try:
            report = state.orchestrator.run(state.profile)
            state.report, state.status, state.error = report, report.status, report.error
        except Exception as e:  # orchestrator already fails closed; this is a last resort
            state.status, state.error = "failed_closed", f"{type(e).__name__}: {str(e)[:200]}"
        finally:
            state.error = redact(state.error)
            state.finished_at = time.time()

    def get(self, run_id: str) -> RunState:
        if run_id not in self.runs:
            raise RunRejected(404, "Unknown run id.")
        return self.runs[run_id]
