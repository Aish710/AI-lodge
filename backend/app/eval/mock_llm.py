"""Scripted stand-in for the language model, used by the evaluation. It never touches the network or an API key.

Scenarios that use it verify the PIPELINE (sanitising, schema validation, name resolution, grounding, fallbacks), not the model.
"""
import copy
import json

from app.llm.client import LLMResponse


class ScriptedLLM:
    model = "mock-model"

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls: list[dict] = []

    def complete(self, system, messages, max_tokens):
        self.calls.append({"system": system, "messages": copy.deepcopy(messages), "max_tokens": max_tokens})
        if not self.replies:
            raise AssertionError("unexpected extra LLM call")
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return LLMResponse(text=r if isinstance(r, str) else json.dumps(r), input_tokens=10, output_tokens=5, latency_seconds=0.001)

    @property
    def all_prompt_text(self) -> str:
        return "\n".join([c["system"] for c in self.calls] + [m["content"] for c in self.calls for m in c["messages"]])


def extraction_reply(**over) -> dict:
    base = {"days": 2, "budget": None, "pace": None, "interests": [], "must_visit_names": [], "skip_names": [],
            "day_start": None, "day_end": None, "value_of_time": None, "max_walking_minutes": None, "unclear": []}
    base.update(over)
    return base


def replan_reply(*ops) -> dict:
    full = []
    for o in ops:
        d = {"op": "remove", "attraction_name": None, "day": None, "day_part": "none", "budget": None, "hotel_name": None}
        d.update(o)
        full.append(d)
    return {"operations": full, "unclear": []}
