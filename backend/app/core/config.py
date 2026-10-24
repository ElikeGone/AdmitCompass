"""Environment loading: repo .env first, then one folder above (grader requirement).

Never prints or logs key values. Already-set environment variables always win.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[3]

# The only model the course key is authorized for. No silent fallback.
AUTHORIZED_MODEL = "gpt-6-luna"
DEFAULT_PORTKEY_BASE_URL = "https://api.portkey.ai/v1"


class MissingAPIKeyError(RuntimeError):
    pass


def candidate_env_files(repo_root: Path = REPO_ROOT) -> list[Path]:
    return [repo_root / ".env", repo_root.parent / ".env"]


def load_environment(repo_root: Path = REPO_ROOT) -> list[Path]:
    """Load .env files in priority order; returns the files that existed (paths only).

    override=False means: values already in os.environ are kept, and the repo
    .env wins over the parent .env because it is loaded first.
    """
    loaded = []
    for path in candidate_env_files(repo_root):
        if path.is_file():
            load_dotenv(path, override=False)
            loaded.append(path)
    return loaded


@dataclass(frozen=True)
class Settings:
    portkey_api_key: str
    portkey_base_url: str
    portkey_provider: str
    model: str
    max_cost_usd_per_run: float

    def __repr__(self) -> str:  # never expose the key
        return f"Settings(model={self.model!r}, base_url={self.portkey_base_url!r}, key=<redacted>)"


def get_settings(repo_root: Path = REPO_ROOT) -> Settings:
    load_environment(repo_root)
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        searched = ", ".join(str(p) for p in candidate_env_files(repo_root))
        raise MissingAPIKeyError(
            "PORTKEY_API_KEY is not set. Add it to a .env file in the project folder "
            f"or the folder one level above (searched: {searched}). See .env.example."
        )
    model = os.getenv("ADMITCOMPASS_MODEL", AUTHORIZED_MODEL).strip()
    if model != AUTHORIZED_MODEL:
        raise ValueError(
            f"ADMITCOMPASS_MODEL={model!r} is not allowed; the course key is authorized only for {AUTHORIZED_MODEL!r}."
        )
    return Settings(
        portkey_api_key=key,
        portkey_base_url=os.getenv("PORTKEY_BASE_URL", DEFAULT_PORTKEY_BASE_URL),
        portkey_provider=os.getenv("PORTKEY_PROVIDER", "openai"),
        model=model,
        max_cost_usd_per_run=float(os.getenv("ADMITCOMPASS_MAX_COST_USD_PER_RUN", "0.25")),
    )


def redact_secrets(text: str | None) -> str | None:
    """Remove secret values (API keys) from any text that may be logged or shown."""
    if not text:
        return text
    for name in ("PORTKEY_API_KEY", "OPENAI_API_KEY"):
        val = os.getenv(name, "").strip()
        if len(val) >= 8:
            text = text.replace(val, "<redacted>")
    return text
