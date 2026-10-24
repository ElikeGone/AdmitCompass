from datetime import date, timedelta
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.core import config
from backend.app.core.usage import append_jsonl, estimate_cost, record_from_usage
from backend.app.schemas.claims import Claim, ClaimLabel, Evidence

EV = dict(source_url="https://example.edu/program", source_title="Program page",
          verified_on=date(2026, 10, 1), excerpt="Program is STEM-designated (CIP 52.1301).")


@pytest.fixture
def clean_env(monkeypatch):
    for k in ("PORTKEY_API_KEY", "ADMITCOMPASS_MODEL"):
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


def make_repo(tmp_path):
    repo = tmp_path / "clone"
    repo.mkdir()
    return repo


# --- environment lookup ---
def test_env_loaded_from_parent_folder(tmp_path, clean_env):
    repo = make_repo(tmp_path)
    (tmp_path / ".env").write_text("PORTKEY_API_KEY=parent-test-value\n")
    assert config.get_settings(repo).portkey_api_key == "parent-test-value"


def test_repo_env_wins_over_parent(tmp_path, clean_env):
    repo = make_repo(tmp_path)
    (tmp_path / ".env").write_text("PORTKEY_API_KEY=parent-test-value\n")
    (repo / ".env").write_text("PORTKEY_API_KEY=repo-test-value\n")
    assert config.get_settings(repo).portkey_api_key == "repo-test-value"


def test_existing_environment_variable_respected(tmp_path, clean_env):
    repo = make_repo(tmp_path)
    (repo / ".env").write_text("PORTKEY_API_KEY=repo-test-value\n")
    clean_env.setenv("PORTKEY_API_KEY", "preset-test-value")
    assert config.get_settings(repo).portkey_api_key == "preset-test-value"


def test_missing_key_clear_message(tmp_path, clean_env):
    with pytest.raises(config.MissingAPIKeyError, match="PORTKEY_API_KEY is not set"):
        config.get_settings(make_repo(tmp_path))


def test_unauthorized_model_rejected(tmp_path, clean_env):
    clean_env.setenv("PORTKEY_API_KEY", "x")
    clean_env.setenv("ADMITCOMPASS_MODEL", "gpt-5.6-luna")
    with pytest.raises(ValueError, match="gpt-6-luna"):
        config.get_settings(make_repo(tmp_path))


def test_settings_repr_hides_key(tmp_path, clean_env):
    clean_env.setenv("PORTKEY_API_KEY", "secret-test-value")
    assert "secret-test-value" not in repr(config.get_settings(make_repo(tmp_path)))


# --- claims ---
def test_valid_verified_claim():
    c = Claim(text="Program is STEM-designated", label="verified_fact", evidence=[EV])
    assert c.label is ClaimLabel.VERIFIED_FACT


def test_verified_claim_without_evidence_rejected():
    with pytest.raises(ValidationError, match="verified_fact"):
        Claim(text="Program is STEM-designated", label="verified_fact")


@pytest.mark.parametrize("bad", [{"source_url": "not-a-url"}, {"verified_on": None},
                                 {"verified_on": date.today() + timedelta(days=5)}])
def test_invalid_evidence_rejected(bad):
    with pytest.raises(ValidationError):
        Evidence(**{**EV, **bad})


@pytest.mark.parametrize("label", ["inference", "unknown", "advice"])
def test_non_verified_labels_need_no_evidence(label):
    assert Claim(text="x", label=label).evidence == []


def test_unknown_label_rejected():
    with pytest.raises(ValidationError):
        Claim(text="x", label="probably_true")


# --- usage logging ---
def test_usage_record_with_cached_tokens(tmp_path):
    usage = {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150,
             "prompt_tokens_details": {"cached_tokens": 64}}
    rec = record_from_usage("gpt-6-luna", usage, 1.23456)
    assert (rec.input_tokens, rec.cached_input_tokens, rec.output_tokens) == (120, 64, 30)
    assert rec.estimated_cost_usd is None and rec.cost_basis.startswith("unknown")
    path = tmp_path / "u.jsonl"
    append_jsonl(rec, path)
    row = json.loads(path.read_text())
    assert row["elapsed_seconds"] == 1.235 and "key" not in json.dumps(row).lower()


def test_usage_missing_values_stay_unknown():
    rec = record_from_usage("gpt-6-luna", {"prompt_tokens": 10, "completion_tokens": 5}, 0.1)
    assert rec.cached_input_tokens is None and rec.total_tokens is None
    assert record_from_usage("gpt-6-luna", None, 0.1).input_tokens is None


def test_cost_only_with_documented_price(monkeypatch):
    from backend.app.core import usage as u
    assert estimate_cost("gpt-6-luna", 100, 0, 10)[0] is None
    monkeypatch.setitem(u.PRICES_PER_MTOK, "test-model", {"input": 1.0, "cached_input": 0.5, "output": 2.0, "source": "test"})
    assert estimate_cost("test-model", 1_000_000, 500_000, 1_000_000)[0] == pytest.approx(2.75)


# --- API ---
def test_health_is_safe(monkeypatch):
    monkeypatch.setenv("PORTKEY_API_KEY", "secret-test-value")
    from backend.app.main import app
    body = TestClient(app).get("/health").json()
    assert body["status"] == "ok" and body["api_key_configured"] is True
    assert "secret-test-value" not in json.dumps(body)
