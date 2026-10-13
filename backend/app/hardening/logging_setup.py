"""Logging policy: metadata only. Redacts anything resembling a key or bearer token from every log record, and
formats the app loggers as one JSON object per line. Request bodies, user text, prompts, model output and query
strings are never passed to a logger by this code base."""
import json
import logging
import re

_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_\-]{8,}"), "[REDACTED_KEY]"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"), "Bearer [REDACTED]"),
    (re.compile(r"(?i)(api[_-]?key|x-api-key|authorization|secret|token)(\"?\s*[:=]\s*\"?)[^\s\",;}]+"), r"\1\2[REDACTED]"),
]
_installed = False


def redact(text: str) -> str:
    for rx, rep in _PATTERNS:
        text = rx.sub(rep, text)
    return text


def install_redaction() -> None:
    """Wrap the log-record factory so EVERY record (any logger, any handler) is redacted at creation."""
    global _installed
    if _installed:
        return
    old = logging.getLogRecordFactory()

    def factory(*a, **kw):
        rec = old(*a, **kw)
        try:
            msg = rec.getMessage()
        except Exception:
            msg = str(rec.msg)
        rec.msg, rec.args = redact(msg), None
        return rec

    logging.setLogRecordFactory(factory)
    _installed = True


_STD = set(logging.LogRecord("x", 0, "", 0, "", (), None).__dict__) | {"message", "asctime", "taskName"}


class MetaFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {"level": record.levelname, "logger": record.name, "msg": record.getMessage()}
        data.update({k: v for k, v in record.__dict__.items() if k not in _STD})
        return redact(json.dumps(data, default=str))


def configure_logging(level: int = logging.INFO) -> None:
    install_redaction()
    lg = logging.getLogger("app")
    lg.setLevel(level)
    if not any(getattr(h, "_meta", False) for h in lg.handlers):
        h = logging.StreamHandler()
        h._meta = True  # type: ignore[attr-defined]
        h.setFormatter(MetaFormatter())
        lg.addHandler(h)
    logging.getLogger("uvicorn.access").disabled = True  # access lines can carry query strings; we log our own metadata
