"""Shared pieces for the opt-in live scripts (ai_selfcheck.py, score_gold.py). Import-safe: nothing here calls a model or reads a key by itself.
The key is read only by AnthropicLLMClient.from_env(); this module never prints it."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent

from app import config  # noqa: E402
from app.llm.client import LLMResponse, LLMUnavailable  # noqa: E402
from app.optimiser.hotel_compare import compare_hotels  # noqa: E402
from app.schemas import Preferences  # noqa: E402

FATAL = {"authentication", "api_error"}  # no point spending more calls: the key or the model name is wrong
ADVICE = {
    "authentication": "The API rejected the key in LLM_API_KEY. Check that it is a current Anthropic API key (not a different provider's key) and has no stray spaces or quotes.",
    "api_error": "The API returned an error. The most common cause is an invalid model name in LLM_MODEL (set to '{model}'). Check the exact model ID in your Anthropic console.",
    "network": "The API could not be reached. Check your internet connection and any proxy or firewall settings.",
    "timeout": "The API did not answer in time.",
    "rate_limited": "The API rate-limited the request. Wait a minute and run again.",
    "call_cap": "The call cap for this script was reached.",
    "error": "An unexpected client error occurred.",
}


class RunAborted(Exception):
    """Raised by Capped when further calls would be wasted. Not a subclass of LLMUnavailable, so the pipeline cannot swallow it."""

    def __init__(self, category: str, model: str):
        self.category, self.model = category, model
        super().__init__(ADVICE.get(category, ADVICE["error"]).format(model=model))


class Capped:
    """Wraps a client: counts calls, hard cap, records every reply (kept in memory only), aborts the run on a fatal error."""

    def __init__(self, inner, cap: int):
        self.inner, self.cap, self.model = inner, cap, inner.model
        self.total_calls = 0
        self.log: list[LLMResponse] = []
        self.failures: list[str] = []

    def complete(self, system, messages, max_tokens):
        if self.total_calls >= self.cap:
            raise RunAborted("call_cap", self.model)
        self.total_calls += 1
        try:
            r = self.inner.complete(system, messages, max_tokens)
        except LLMUnavailable as e:
            self.failures.append(e.category)
            if e.category in FATAL or len(self.failures) >= 3:
                raise RunAborted(e.category, self.model) from None
            raise
        self.log.append(r)
        return r


def gate(script: str, cap: int) -> str | None:
    """None when a live run may proceed, otherwise the plain message to print. Never echoes the key."""
    if os.environ.get("RUN_LIVE_LLM_EVAL") != "1":
        return f"{script} is opt-in and made no model calls. To run it: RUN_LIVE_LLM_EVAL=1 plus LLM_API_KEY and LLM_MODEL (at most {cap} calls)."
    missing = [v for v in ("LLM_API_KEY", "LLM_MODEL") if not os.environ.get(v)]
    if missing:
        return (f"Cannot run live: {' and '.join(missing)} {'is' if len(missing) == 1 else 'are'} not set. Put {'it' if len(missing) == 1 else 'them'} in backend/.env (copy .env.example) "
                f"or export them in this shell, then run again. Nothing was called.")
    return None


def git_hash() -> str:
    try:
        h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
        return h + (" + uncommitted changes" if dirty else "")
    except Exception:
        return "unknown"


def real_result(ds):
    """A real hotel comparison computed by the solver for this city (the model only words it)."""
    hotels = list(ds.hotels)
    first = next(iter(ds.attractions))
    pr = Preferences(days=2, must_visit=[first], day_start=ds.city.default_day_start, day_end=ds.city.default_day_end,
                     value_of_time_per_hour=ds.city.default_value_of_time_per_hour)
    return compare_hotels(pr, hotels, ds, time_limit=60)


def load_env_file() -> None:
    """Load backend/.env into the process environment WITHOUT overriding variables already set, and without printing anything."""
    p = Path(os.environ.get("LIVE_ENV_FILE") or ROOT / ".env")
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if not os.environ.get(k.strip()):
                os.environ[k.strip()] = v.strip().strip('"').strip("'")
