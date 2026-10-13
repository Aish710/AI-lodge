"""Scripted mock LLM for tests: records every prompt, counts calls, can raise LLMUnavailable. Never touches the network."""
import copy
import json

from app.llm.client import LLMResponse


class MockLLM:
    model = "mock-model"

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls: list[dict] = []

    def complete(self, system, messages, max_tokens):
        self.calls.append({"system": system, "messages": copy.deepcopy(messages), "max_tokens": max_tokens})
        if not self.replies:
            raise AssertionError("unexpected extra LLM call (call cap exceeded)")
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        if not isinstance(r, str):
            r = json.dumps(r)
        return LLMResponse(text=r, input_tokens=10, output_tokens=5, latency_seconds=0.001)

    @property
    def all_prompt_text(self) -> str:
        parts = []
        for c in self.calls:
            parts.append(c["system"])
            parts += [m["content"] for m in c["messages"]]
        return "\n".join(parts)


def extraction(**over):
    base = {"days": 2, "budget": None, "pace": None, "interests": [], "must_visit_names": [], "skip_names": [],
            "day_start": None, "day_end": None, "value_of_time": None, "max_walking_minutes": None, "unclear": []}
    base.update(over)
    return base


def replan_out(*ops, unclear=()):
    full = []
    for o in ops:
        d = {"op": "remove", "attraction_name": None, "day": None, "day_part": "none", "budget": None, "hotel_name": None}
        d.update(o)
        full.append(d)
    return {"operations": full, "unclear": list(unclear)}
