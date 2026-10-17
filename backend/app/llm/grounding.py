"""Grounding checker: is every quantity and name in an LLM explanation present in the computed facts?

Rejects (a) any number, percentage or time not found in the facts, (b) spelled-out numbers followed by a unit or
noun whose value is not in the facts, and (c) any dataset attraction/hotel name that is not in the facts.
It is deliberately strict: a false reject only means the template text is shown; a false accept would let an invented
figure through. Known gaps are listed in docs/LLM_DESIGN.md.
"""
import re
from dataclasses import dataclass, field
from decimal import Decimal

from app.llm.names import normalise

_TIME = re.compile(r"(?<![\d:])([01]?\d|2[0-3]):([0-5]\d)(?![\d:])")
# A duration the facts print as "158 min (2:38)": its parts may be written as "2 hours 38 minutes". Only this parenthesised form is split, so a clock time
# such as 09:30 does not make a bare 30 acceptable.
_DURATION = re.compile(r"\bmin\s*\((\d{1,3}):([0-5]\d)\)")
_NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(\s?[kK]\b)?(\s?%)?")

_ONES = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}
_TENS = {"thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_SCALE = {"hundred": 100, "thousand": 1000, "million": 1_000_000}
_WORDS = sorted(list(_ONES) + list(_TENS) + list(_SCALE), key=len, reverse=True)
_UNITS = (r"minutes?|mins?|hours?|hrs?|yen|jpy|sgd|krw|won|myr|ringgit|cny|yuan|rmb|usd|dollars?|days?|nights?|activit(?:y|ies)|stops?|sights?|attractions?|"
          r"places?|hotels?|moves?|changes?|percent|per\s*cent")
_SPELLED = re.compile(r"\b((?:(?:" + "|".join(_WORDS) + r")(?:[\s-]+(?:and\s+)?)?)+)\s+(" + _UNITS + r")\b", re.IGNORECASE)


def _words_to_int(s: str) -> int | None:
    total, current, seen = 0, 0, False
    for w in re.split(r"[\s-]+", s.lower().strip()):
        if w in ("", "and"):
            continue
        seen = True
        if w in _ONES:
            current += _ONES[w]
        elif w in _TENS:
            current += _TENS[w]
        elif w == "hundred":
            current = max(current, 1) * 100
        elif w in _SCALE:
            total += max(current, 1) * _SCALE[w]
            current = 0
        else:
            return None
    return total + current if seen else None


def _dec(s: str) -> Decimal:
    return Decimal(s).normalize()


@dataclass
class Tokens:
    numbers: set = field(default_factory=set)   # Decimal values (absolute)
    percents: set = field(default_factory=set)
    times: set = field(default_factory=set)     # "HH:MM"
    raw: list = field(default_factory=list)     # (display token, kind, value) in order of appearance


def extract_tokens(text: str) -> Tokens:
    t = Tokens()
    t_text = text.replace("−", "-").replace("–", "-")
    for m in _TIME.finditer(t_text):
        hhmm = f"{int(m.group(1)):02d}:{m.group(2)}"
        t.times.add(hhmm)
        t.raw.append((m.group(0), "time", hhmm))
    t_text = _TIME.sub(" ", t_text)
    for m in _NUM.finditer(t_text):
        val = _dec(m.group(1).replace(",", "") + (m.group(2) or ""))
        if m.group(3):  # 1.5k -> 1500
            val = (val * 1000).normalize()
        if m.group(4):
            t.percents.add(val)
            t.raw.append((m.group(0).strip(), "pct", val))
        else:
            t.numbers.add(val)
            t.raw.append((m.group(0).strip(), "num", val))
    return t


@dataclass
class GroundingResult:
    ok: bool
    checked: int
    rejected_tokens: list[str]


def check_grounding(text: str, allowed_text: str, allowed_values: list, allowed_ids_forms: set[str],
                    all_forms: dict[str, str]) -> GroundingResult:
    """allowed_ids_forms: normalised names/aliases of places that ARE in the facts.
    all_forms: normalised form -> display name for every dataset place (attractions, aliases, hotels)."""
    allowed = extract_tokens(allowed_text)
    nums = set(allowed.numbers)
    for v in allowed_values:
        d = _dec(str(abs(v)))
        nums.add(d)
    for m in _DURATION.finditer(allowed_text):
        nums.add(_dec(str(int(m.group(1)))))
        nums.add(_dec(str(int(m.group(2)))))
    got = extract_tokens(text)
    rejected: list[str] = []
    checked = 0
    for display, kind, val in got.raw:
        checked += 1
        if kind == "time":
            ok = val in allowed.times
        elif kind == "pct":
            ok = val in allowed.percents
        else:
            ok = val in nums
        if not ok:
            rejected.append(display)
    for m in _SPELLED.finditer(text):
        checked += 1
        val = _words_to_int(m.group(1))
        unit = m.group(2).lower()
        is_pct = "per" in unit and ("cent" in unit)
        if val is None or is_pct or _dec(str(val)) not in nums:
            rejected.append(f"{m.group(1).strip()} {m.group(2)}")
    ntext = normalise(text)
    for form, display in all_forms.items():
        if form in allowed_ids_forms:
            continue
        if re.search(r"(?<![0-9a-z])" + re.escape(form) + r"(?![0-9a-z])", ntext):
            checked += 1
            rejected.append(f"name:{display}")
    return GroundingResult(ok=not rejected, checked=checked, rejected_tokens=rejected)
