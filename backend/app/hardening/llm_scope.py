"""Per-request LLM scoping: global call budget (circuit breaker), request deadline, usage stats.
Every real model call is counted (retries included). When the cap is reached the LLM is disabled and the app runs in
sample mode. Per process, in memory; the provider spending cap is the real backstop."""
from collections import deque
from dataclasses import dataclass

from fastapi import Depends, Request

from app import config, runtime
from app.llm.client import LLMClient, LLMResponse, LLMUnavailable, get_llm_client

DAY_SECONDS = 24 * 3600


class LLMBudget:
    def __init__(self, cap: int):
        self.cap = cap
        self._calls: deque = deque()

    def _prune(self) -> None:
        cutoff = runtime.now() - DAY_SECONDS
        while self._calls and self._calls[0] <= cutoff:
            self._calls.popleft()

    def used(self) -> int:
        self._prune()
        return len(self._calls)

    def exhausted(self) -> bool:
        return self.used() >= self.cap

    def record(self) -> None:
        self._calls.append(runtime.now())

    def reset(self) -> None:
        self._calls.clear()


@dataclass
class LLMStats:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class ScopedLLM:
    """Wraps any LLMClient (real or mock) for one request."""

    def __init__(self, base: LLMClient, budget: LLMBudget, deadline_at: float, stats: LLMStats):
        self._base, self._budget, self._deadline_at, self._stats = base, budget, deadline_at, stats
        self.model = getattr(base, "model", "unknown")

    def complete(self, system: str, messages: list[dict], max_tokens: int) -> LLMResponse:
        if self._budget.exhausted():
            raise LLMUnavailable("daily_cap")
        if self._deadline_at - runtime.now() < config.LLM_TIMEOUT_SECONDS:  # a call could not finish inside the deadline
            raise LLMUnavailable("deadline")
        self._budget.record()
        self._stats.calls += 1
        r = self._base.complete(system, messages, max_tokens)
        self._stats.input_tokens += r.input_tokens
        self._stats.output_tokens += r.output_tokens
        return r


def llm_for_request(request: Request, base: LLMClient | None = Depends(get_llm_client)) -> LLMClient | None:
    """Dependency used by every LLM-capable route. Returns None (sample mode) with a note when the model cannot be used."""
    st = request.state
    st.llm_stats = stats = LLMStats()
    st.llm_note = None
    budget: LLMBudget = request.app.state.llm_budget
    cfg = request.app.state.hconf
    if base is None:
        st.llm_note = "Sample mode: no language model is configured."
        return None
    if budget.exhausted():
        st.llm_note = "The daily limit for language-model calls has been reached, so sample mode is active."
        st.llm_limit_reached = True
        return None
    deadline_at = getattr(st, "t0", runtime.now()) + cfg.request_deadline_seconds
    if deadline_at - runtime.now() < config.LLM_TIMEOUT_SECONDS:
        st.llm_note = "The request deadline is too short for a language-model call, so sample mode is used."
        return None
    return ScopedLLM(base, budget, deadline_at, stats)
