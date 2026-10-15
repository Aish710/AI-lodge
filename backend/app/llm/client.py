"""LLM client: one-method Protocol, an Anthropic SDK implementation, and a safe error type.

No tools, no web access, no streaming. SDK auto-retries are disabled (max_retries=0) so the per-request call caps
in config.py are exact. Any failure raises LLMUnavailable with a safe message; callers fall back to sample mode.
The API key is never put in messages, logs or repr().
"""
import logging
import os
import time
from dataclasses import dataclass
from typing import Protocol

from app import config
from app.llm.endpoint import Endpoint, resolve_endpoint

log = logging.getLogger("app.llm")  # metadata only: never prompts, user text or keys


class LLMUnavailable(Exception):
    """The model could not be used. `category` is a safe, fixed label."""

    def __init__(self, category: str = "unavailable"):
        super().__init__(f"The language model is unavailable ({category}). Sample mode is used instead.")
        self.category = category


@dataclass(frozen=True)
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_seconds: float = 0.0
    stop_reason: str | None = None


class LLMClient(Protocol):
    model: str

    def complete(self, system: str, messages: list[dict], max_tokens: int) -> LLMResponse: ...


class AnthropicLLMClient:
    """Anthropic SDK wrapper. Reads LLM_API_KEY / LLM_MODEL (and optional LLM_EFFORT) from the environment."""

    def __init__(self, api_key: str, model: str, effort: str = config.LLM_EFFORT_DEFAULT,
                 timeout: float = config.LLM_TIMEOUT_SECONDS, endpoint: Endpoint | None = None):
        import anthropic  # imported lazily so sample mode and tests never need the SDK to be configured

        self.model = model
        self._effort = effort
        self.endpoint = endpoint or resolve_endpoint(None)
        self.endpoint_host = self.endpoint.host
        kwargs = {"base_url": self.endpoint.base_url} if self.endpoint.base_url else {}  # unset: exactly the SDK default, as before
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=0, **kwargs)

    def __repr__(self) -> str:  # never expose the key
        return f"AnthropicLLMClient(model={self.model!r}, endpoint={self.endpoint_host!r}, api_key='***')"

    @classmethod
    def from_env(cls) -> "AnthropicLLMClient | None":
        key, model = os.environ.get("LLM_API_KEY", ""), os.environ.get("LLM_MODEL", "")
        if not (key and model):
            return None
        effort = os.environ.get("LLM_EFFORT", config.LLM_EFFORT_DEFAULT)
        endpoint = resolve_endpoint(os.environ.get("LLM_BASE_URL"))
        if endpoint.error:  # refused: stay in sample mode rather than send a key or text to an unsafe address
            log.error("llm_endpoint_refused", extra={"reason": endpoint.error})
            return None
        for w in endpoint.warnings:
            log.warning("llm_endpoint_normalised", extra={"host": endpoint.host, "note": w})
        return cls(key, model, effort, endpoint=endpoint)

    def complete(self, system: str, messages: list[dict], max_tokens: int) -> LLMResponse:
        import anthropic

        kwargs = dict(model=self.model, max_tokens=max_tokens, system=system, messages=messages)
        if self._effort:
            kwargs["output_config"] = {"effort": self._effort}
        t0 = time.perf_counter()
        try:
            resp = self._client.messages.create(**kwargs)
        except anthropic.APITimeoutError:
            raise LLMUnavailable("timeout") from None
        except anthropic.RateLimitError:
            raise LLMUnavailable("rate_limited") from None
        except anthropic.AuthenticationError:
            raise LLMUnavailable("authentication") from None
        except anthropic.APIConnectionError:
            raise LLMUnavailable("network") from None
        except anthropic.APIStatusError:
            raise LLMUnavailable("api_error") from None
        except Exception:  # never let an SDK detail (which could echo request data) escape
            raise LLMUnavailable("error") from None
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        usage = getattr(resp, "usage", None)
        return LLMResponse(text=text, input_tokens=getattr(usage, "input_tokens", 0) or 0,
                           output_tokens=getattr(usage, "output_tokens", 0) or 0,
                           latency_seconds=round(time.perf_counter() - t0, 3), stop_reason=getattr(resp, "stop_reason", None))


def get_llm_client() -> "LLMClient | None":
    """FastAPI dependency. Tests override it (app.dependency_overrides) with a mock. None = sample mode."""
    return AnthropicLLMClient.from_env()
