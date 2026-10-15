"""LLM_BASE_URL (third-party gateway support), MOCK only: the SDK is replaced by a recorder, nothing touches the network or a real key."""
import logging
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.llm import client as client_mod
from app.llm.client import AnthropicLLMClient
from app.llm.endpoint import DEFAULT_HOST, resolve_endpoint
from app.main import app

SECRET = "sk-test-SECRET-KEY-9f8e7d6c5b4a"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import live_common as lc  # noqa: E402


@pytest.fixture
def sdk(monkeypatch):
    """Replace anthropic.Anthropic with a recorder that keeps the constructor kwargs."""
    seen = {}

    class FakeAnthropic:
        def __init__(self, **kw):
            seen.update(kw)

    fake = types.ModuleType("anthropic")
    fake.Anthropic = FakeAnthropic
    for name in ("APITimeoutError", "RateLimitError", "AuthenticationError", "APIConnectionError", "APIStatusError"):
        setattr(fake, name, type(name, (Exception,), {}))
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    return seen


def _env(monkeypatch, base=None):
    monkeypatch.setenv("LLM_API_KEY", SECRET)
    monkeypatch.setenv("LLM_MODEL", "claude-haiku-4-5-20251001")
    if base is not None:
        monkeypatch.setenv("LLM_BASE_URL", base)


def test_unset_means_the_sdk_default_exactly_as_before(sdk, monkeypatch):
    _env(monkeypatch)
    c = AnthropicLLMClient.from_env()
    assert "base_url" not in sdk and sdk["max_retries"] == 0 and sdk["api_key"] == SECRET
    assert c.endpoint_host == DEFAULT_HOST and c.endpoint.relay is False


def test_base_url_reaches_the_sdk_constructor(sdk, monkeypatch):
    _env(monkeypatch, "https://api.apiyi.com")
    c = AnthropicLLMClient.from_env()
    assert sdk["base_url"] == "https://api.apiyi.com"
    assert c.endpoint_host == "api.apiyi.com" and c.endpoint.relay is True


def test_trailing_v1_and_slash_are_stripped_with_a_warning_that_names_only_the_host(sdk, monkeypatch, caplog):
    _env(monkeypatch, "https://api.apiyi.com/v1/")
    with caplog.at_level(logging.WARNING):
        AnthropicLLMClient.from_env()
    assert sdk["base_url"] == "https://api.apiyi.com"
    assert "llm_endpoint_normalised" in caplog.text
    assert SECRET not in caplog.text and "/v1" not in "".join(getattr(r, "host", "") for r in caplog.records)


@pytest.mark.parametrize("bad", ["http://relay.example.com", "ftp://relay.example.com", "relay.example.com", "https://user:pw@relay.example.com", "https://relay.example.com/?k=1", "https://"])
def test_anything_but_plain_https_is_refused_and_the_llm_stays_off(sdk, monkeypatch, caplog, bad):
    _env(monkeypatch, bad)
    assert resolve_endpoint(bad).error
    with caplog.at_level(logging.ERROR):
        assert AnthropicLLMClient.from_env() is None
    assert sdk == {}                                              # the SDK was never constructed: no key, no text can go anywhere
    assert "llm_endpoint_refused" in caplog.text and SECRET not in caplog.text and "pw@" not in caplog.text


def test_health_shows_the_host_only_and_never_the_key_or_the_path(monkeypatch):
    _env(monkeypatch, "https://relay.example.com/gateway/")
    with TestClient(app) as c:
        h = c.get("/health").json()
        text = c.get("/health").text
    assert h["llm_configured"] is True and h["llm_endpoint"] == "relay.example.com" and h["llm_relay"] is True
    assert SECRET not in text and "/gateway" not in text and "https://" not in text


def test_health_in_sample_mode_has_no_endpoint_fields_and_a_refused_url_means_sample_mode(monkeypatch):
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok", "mode": "sample", "llm_configured": False, "llm_mode": "sample", "llm_limit_reached": False}
    _env(monkeypatch, "http://relay.example.com")
    with TestClient(app) as c:
        h = c.get("/health").json()
    assert h["mode"] == "sample" and h["llm_configured"] is False and "llm_endpoint" not in h


def test_the_key_and_url_never_appear_in_repr_or_startup_logs(sdk, monkeypatch, caplog):
    _env(monkeypatch, "https://relay.example.com/gateway")
    with caplog.at_level(logging.DEBUG):
        c = AnthropicLLMClient.from_env()
        with TestClient(app) as t:
            t.get("/health")
    assert SECRET not in repr(c) and SECRET not in caplog.text
    blob = caplog.text + " ".join(str(v) for r in caplog.records for v in vars(r).values())       # messages AND structured fields
    assert "/gateway" not in blob and SECRET not in blob
    assert any(getattr(r, "host", None) == "relay.example.com" for r in caplog.records)         # the host is logged, nothing more


def test_a_rejected_key_message_names_the_host_and_never_the_key():
    msg = str(lc.RunAborted("authentication", "claude-haiku-4-5-20251001", "api.apiyi.com"))
    assert "rejected by api.apiyi.com" in msg and SECRET not in msg


def test_a_bad_model_message_mentions_the_gateway_root_domain_hint():
    msg = str(lc.RunAborted("api_error", "not-a-model", "api.apiyi.com"))
    assert "LLM_MODEL" in msg and "api.apiyi.com" in msg and "/v1" in msg


def test_report_stamp_says_relay_only_when_a_base_url_is_set():
    class C:  # what the scripts see
        def __init__(self, host, relay):
            self.host, self.relay = host, relay
    direct = lc.endpoint_stamp(C(DEFAULT_HOST, False))
    relayed = lc.endpoint_stamp(C("api.apiyi.com", True))
    assert "api.anthropic.com" in direct and "relay" not in direct
    assert "api.apiyi.com" in relayed and "third-party relay" in relayed and "pass through that gateway" in relayed


def test_the_live_gate_refuses_an_unsafe_base_url_before_anything_runs(monkeypatch):
    monkeypatch.setenv("RUN_LIVE_LLM_EVAL", "1")
    _env(monkeypatch, "http://relay.example.com")
    msg = lc.gate("scripts/x.py", 10)
    assert "https://" in msg and "Nothing was called" in msg and SECRET not in msg
