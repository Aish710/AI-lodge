"""Unsupported-claims guard for explanations. The grounding check looks at numbers and names only, so a model could still write that a place is quiet, step-free or safe for
children. The app has no data for any of that. A sentence that asserts it is rejected (the template is shown) unless the term appears VERBATIM in the computed facts.
The term list is a data file (unsupported_terms.json) with English, Malay, Korean and Chinese equivalents."""
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

_FILE = Path(__file__).with_name("unsupported_terms.json")
LANGS = ("en", "ms", "ko", "zh")
_LATIN = re.compile(r"^[\x00-\x7f\s'-]+$")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s))).strip().lower()


@lru_cache(maxsize=1)
def load_terms() -> dict[str, dict[str, list[str]]]:
    return json.loads(_FILE.read_text(encoding="utf-8"))["groups"]


def _pattern(term: str) -> re.Pattern:
    prefix = term.endswith("*")
    k = _norm(term[:-1] if prefix else term)
    if _LATIN.match(k):
        return re.compile(r"(?<![a-z0-9])" + re.escape(k) + ("" if prefix else r"(?![a-z0-9])"))
    return re.compile(re.escape(k))


def unsupported_claims(text: str, facts_text: str = "") -> list[tuple[str, str]]:
    """[(group, term)] for every term that appears in `text` but NOT in the facts. A term present in the facts verbatim is the data speaking, so it is allowed."""
    t, f = _norm(text), _norm(facts_text)
    found = []
    for group, by_lang in load_terms().items():
        for lang in LANGS:
            for term in by_lang.get(lang, []):
                pat = _pattern(term)
                if pat.search(t) and not pat.search(f):
                    found.append((group, term.rstrip("*")))
    return found
