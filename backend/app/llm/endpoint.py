"""The optional LLM gateway ("relay"): LLM_BASE_URL, validated before it is ever used.

Some providers sell access to the same models through a third-party gateway whose Anthropic-protocol endpoint is its ROOT domain
(for example https://api.example.com, with no /v1). The SDK adds the path itself, so a trailing /v1 or slash is stripped with a warning.
Only https is accepted: the key and the user's cleaned text travel to that host, so a plain-http or credentialed URL is refused and the
app stays in sample mode. The full URL is never logged, returned or stored beyond its host; the key is never part of any of this."""
from dataclasses import dataclass
from urllib.parse import urlsplit

DEFAULT_HOST = "api.anthropic.com"


@dataclass(frozen=True)
class Endpoint:
    base_url: str | None          # normalised, passed to the SDK; None = the SDK default
    host: str                     # what may be shown: host (and port), nothing else
    relay: bool                   # True whenever LLM_BASE_URL is set
    warnings: tuple[str, ...] = ()
    error: str | None = None      # set when the value is refused; the LLM then stays off


def resolve_endpoint(raw: str | None) -> Endpoint:
    value = (raw or "").strip()
    if not value:
        return Endpoint(None, DEFAULT_HOST, False)
    try:
        parts = urlsplit(value)
        host = parts.hostname
        port = parts.port
    except ValueError:
        return Endpoint(None, "invalid", True, error="LLM_BASE_URL is not a valid URL.")
    if parts.scheme.lower() != "https":
        return Endpoint(None, host or "invalid", True, error="LLM_BASE_URL must start with https:// (the key and your text would travel to it).")
    if not host:
        return Endpoint(None, "invalid", True, error="LLM_BASE_URL has no host.")
    if parts.username or parts.password or parts.query or parts.fragment:
        return Endpoint(None, host, True, error="LLM_BASE_URL must be a plain address: no credentials, query or fragment.")
    path = parts.path.rstrip("/")
    warnings: list[str] = []
    if path.lower().endswith("/v1"):
        path = path[:-3].rstrip("/")
        warnings.append("LLM_BASE_URL ended in /v1; it was removed because the SDK adds the path itself (use the root domain).")
    if parts.path.endswith("/") and parts.path != "/":
        warnings.append("LLM_BASE_URL had a trailing slash; it was removed.")
    shown = host if port is None else f"{host}:{port}"
    return Endpoint(f"https://{shown}{path}", shown, True, tuple(warnings))
