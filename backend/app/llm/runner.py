"""Shared call-validate-retry loop for JSON-producing LLM calls. Hard cap on calls; metadata-only logging."""
import json
import logging
import re
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from app.config import get_settings

from app.llm.client import LLMClient, LLMUnavailable
from app.llm.leakguard import scrub
from app.llm.prompts import RETRY_PREFIX

log = logging.getLogger("app.llm")


@dataclass
class Outcome:
    parsed: BaseModel | None
    raw: dict | None
    call_count: int
    unavailable: bool = False
    error: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency: float = 0.0
    removed: int = 0   # strings of model text dropped by the leak guard (prompt text, a key, an email address...)


def _json_object(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b < a:
        raise ValueError("reply is not a JSON object")
    obj = json.loads(t[a:b + 1])
    if not isinstance(obj, dict):
        raise ValueError("reply is not a JSON object")
    return obj


def _problems(e: Exception) -> str:
    if isinstance(e, ValidationError):  # field paths and messages only: never echo the offending values
        return "; ".join(f"{'.'.join(str(x) for x in err['loc']) or 'reply'}: {err['msg']}" for err in e.errors()[:8])[:600]
    return "the reply was not valid JSON"


def call_json(client: LLMClient, system: str, user_content: str, model_cls: type[BaseModel], max_tokens: int,
              max_calls: int, op: str) -> Outcome:
    messages = [{"role": "user", "content": user_content}]
    out = Outcome(parsed=None, raw=None, call_count=0)
    for _ in range(max_calls):
        try:
            resp = client.complete(system, messages, max_tokens)
        except LLMUnavailable as e:
            out.unavailable = True
            log.info("llm_call", extra={"op": op, "outcome": f"unavailable:{e.category}", "calls": out.call_count})
            return out
        out.call_count += 1
        out.input_tokens += resp.input_tokens
        out.output_tokens += resp.output_tokens
        out.latency += resp.latency_seconds
        try:
            raw = _json_object(resp.text)
            raw, removed = scrub(raw, system, get_settings().llm_api_key)   # model free text that quotes the prompt or a secret never reaches a screen
            parsed = model_cls.model_validate(raw)
            out.removed = removed
        except (ValueError, ValidationError) as e:
            out.error = _problems(e)
            messages = messages + [{"role": "assistant", "content": resp.text[:2000] or "(empty)"},
                                   {"role": "user", "content": f"{RETRY_PREFIX} {out.error}"}]
            continue
        out.parsed, out.raw, out.error = parsed, raw, None
        break
    log.info("llm_call", extra={"op": op, "outcome": "ok" if out.parsed else "invalid", "calls": out.call_count,
                                "in_tokens": out.input_tokens, "out_tokens": out.output_tokens, "latency": round(out.latency, 3)})
    return out
