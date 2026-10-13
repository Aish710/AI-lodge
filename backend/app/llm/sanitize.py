"""Input sanitiser for user text that will be shown to the LLM.

It does NOT try to detect prompt injection (keyword filters are brittle and give false confidence).
Defence is structural: the model's output is only a proposal that deterministic code validates, and the
model has no tools and cannot set safety flags. The sanitiser just makes the text well-formed and clearly
delimited data: bounded length, no control/invisible/bidi characters, normalised unicode, and no way to
close the data tag from inside the text.
"""
import re
import unicodedata
from dataclasses import dataclass

TAG = "user_request"
_TAG_RE = re.compile(r"<\s*/?\s*" + TAG + r"\b[^>]*>", re.IGNORECASE)


class InputTooLong(ValueError):
    def __init__(self, length: int, limit: int):
        super().__init__(f"Input is {length} characters; the limit is {limit}. Shorten it (it was not truncated or processed).")
        self.length, self.limit = length, limit


class EmptyInput(ValueError):
    pass


@dataclass(frozen=True)
class Sanitised:
    text: str          # cleaned text, no wrapper
    wrapped: str       # <user_request>\n...\n</user_request>
    removed_chars: int
    original_length: int


def _strip_invisible(s: str) -> tuple[str, int]:
    out, removed = [], 0
    for ch in s:
        cat = unicodedata.category(ch)
        if ch in "\n\r\t   ":
            out.append(" ")  # whitespace-like: becomes a space (collapsed below)
        elif cat in ("Cc", "Cf", "Cs", "Co", "Cn"):  # control, format (zero-width, bidi overrides), surrogate, private, unassigned
            removed += 1
        else:
            out.append(ch)
    return "".join(out), removed


def sanitise_user_text(text: str, max_chars: int) -> Sanitised:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if len(text) > max_chars:
        raise InputTooLong(len(text), max_chars)
    s = unicodedata.normalize("NFKC", text)
    s, removed = _strip_invisible(s)
    s = re.sub(r"\s+", " ", s).strip()
    s = _TAG_RE.sub("[tag removed]", s)  # neutralise literal opening/closing data tags (after NFKC, so fullwidth forms are caught)
    if len(s) > max_chars:  # NFKC can expand some characters
        raise InputTooLong(len(s), max_chars)
    if not s:
        raise EmptyInput("Input is empty after removing control characters.")
    return Sanitised(text=s, wrapped=f"<{TAG}>\n{s}\n</{TAG}>", removed_chars=removed, original_length=len(text))
