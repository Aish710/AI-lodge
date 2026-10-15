"""A deterministic RULE-BASED stand-in for the model, used ONLY by scripts/score_gold.py to give a reference score with zero model calls.
It is deliberately simple (regexes + alias scanning) and is not tuned to the gold set. It is NOT a language model and proves nothing about one."""
import json
import re

from app.llm.client import LLMResponse

WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7}
DAYS = re.compile(r"(\d+|one|two|three|four|five|six|seven)\s*(?:days?|日間|日|天|일|hari)", re.I)
MONEY_BEFORE = re.compile(r"(S\$|RM|SGD|MYR|JPY|KRW|[¥￥₩$])\s?([\d,]+)")
MONEY_AFTER = re.compile(r"([\d,]+)\s?(yen|won|ringgit|円|원|SGD)", re.I)
SKIP_CUE = re.compile(r"(skip|not interested in|no)\s+$", re.I)


class RuleBasedBaseline:
    model = "rule-based baseline v1"

    def __init__(self, all_ds):
        self.all_ds = all_ds
        self.total_calls = 0

    def complete(self, system, messages, max_tokens):
        self.total_calls += 1
        text = messages[0]["content"]
        m = DAYS.search(text)
        days = None
        if m:
            days = int(m.group(1)) if m.group(1).isdigit() else WORDS[m.group(1).lower()]
        if re.search(r"\b99\b", text):  # gullible on purpose: the code-side bounds, not this stand-in, must stop it
            days = 99
        budget = None
        b = MONEY_BEFORE.search(text)
        if b:
            budget = {"amount": float(b.group(2).replace(",", "")), "currency": b.group(1), "strict": False}
        else:
            a = MONEY_AFTER.search(text)
            if a:
                budget = {"amount": float(a.group(1).replace(",", "")), "currency": a.group(2), "strict": False}
        pace = next((p for p in ("relaxed", "packed", "balanced") if p in text.lower()), None)
        must, skip = [], []
        for ds in self.all_ds.values():
            for att in ds.attractions.values():
                for form in sorted({att.name, *att.aliases}, key=len, reverse=True):
                    i = text.lower().find(form.lower())
                    if i >= 0 and len(form) >= 3:
                        (skip if SKIP_CUE.search(text[max(0, i - 12):i]) else must).append(form)
                        break
        out = {"days": days, "budget": budget, "pace": pace, "interests": [], "must_visit_names": must, "skip_names": skip,
               "day_start": None, "day_end": None, "value_of_time": None, "max_walking_minutes": None, "unclear": []}
        return LLMResponse(text=json.dumps(out), input_tokens=0, output_tokens=0, latency_seconds=0.0)
