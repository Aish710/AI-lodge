"""Code-side guard on free text that came from the model and is about to be shown: it must never contain the system prompt, a secret or another person's contact
details. This does not try to understand the text (that is brittle); it removes exactly the things that must never reach a screen, whatever the model was told."""
import re
import unicodedata

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_KEYLIKE = re.compile(r"\bsk-[A-Za-z0-9_-]{6,}|\b(?:api[_ -]?key|secret|bearer|authorization)\b\s*[:=]|\b[A-Za-z0-9+/_-]{32,}\b", re.I)
_PROMPT_WORDS = re.compile(r"system prompt|developer message|hidden prompt|my instructions (?:are|say)", re.I)
_PHONE = re.compile(r"(?<!\d)(?:\+?\d[\s().-]?){9,}\d")
WINDOW = 40


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s)).strip().lower()


def forbidden(text: str, system: str = "", secret: str = "", *, phones: bool = True) -> bool:
    """True if `text` must not be shown: it quotes the system prompt (any 40-character stretch), holds a key-like token, an email address or phone number,
    mentions a hidden prompt, or contains the configured secret itself."""
    if not text:
        return False
    if _EMAIL.search(text) or _KEYLIKE.search(text) or _PROMPT_WORDS.search(text) or (phones and _PHONE.search(text)):
        return True
    low = _norm(text)
    if secret and len(secret) >= 8 and secret.lower() in low:
        return True
    s = _norm(system)
    return bool(s) and len(low) >= WINDOW and any(s[i:i + WINDOW] in low for i in range(0, max(1, len(s) - WINDOW + 1), 10))


def scrub(value, system: str = "", secret: str = ""):
    """(cleaned copy of a JSON-like value, number of strings removed). Strings in lists are dropped; a forbidden string in a field becomes None."""
    removed = 0

    def walk(v):
        nonlocal removed
        if isinstance(v, str):
            if forbidden(v, system, secret):
                removed += 1
                return None
            return v
        if isinstance(v, list):
            out = []
            for x in v:
                y = walk(x)
                if y is not None or not isinstance(x, str):
                    out.append(y)
            return out
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        return v
    return walk(value), removed
