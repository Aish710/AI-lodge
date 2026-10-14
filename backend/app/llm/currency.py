"""Currency resolution for amounts the user typed, done in CODE with the labelled SAMPLE rates.

The model only reports the currency as written (a code such as "KRW", or a symbol/word such as "¥", "$", "RM"). This module decides:
  * an unambiguous code or symbol is mapped to its code;
  * a code that is neither the selected city's currency nor its display currency is NOT converted (there is no rate for that pair):
    the user is asked to restate it;
  * an ambiguous symbol is never guessed: "¥" is read through the selected city's currency (yen in a yen city, yuan in a yuan city) and
    otherwise the user is asked to confirm; "$" (US, Singapore, Hong Kong, ... dollars) is always confirmed.
"""
import re
from dataclasses import dataclass

from app.data.loader import Dataset

SUPPORTED_CODES = ("SGD", "JPY", "KRW", "MYR", "CNY")

_UNAMBIGUOUS = {
    "SGD": "SGD", "S$": "SGD", "SG$": "SGD", "SINGAPORE DOLLAR": "SGD", "SINGAPORE DOLLARS": "SGD",
    "JPY": "JPY", "円": "JPY", "YEN": "JPY", "JAPANESE YEN": "JPY",
    "KRW": "KRW", "₩": "KRW", "원": "KRW", "WON": "KRW", "KOREAN WON": "KRW",
    "MYR": "MYR", "RM": "MYR", "RINGGIT": "MYR", "MALAYSIAN RINGGIT": "MYR",
    "CNY": "CNY", "RMB": "CNY", "YUAN": "CNY", "元": "CNY", "块": "CNY", "人民币": "CNY",
    "USD": "USD", "US$": "USD", "US DOLLAR": "USD", "US DOLLARS": "USD",
}
_AMBIGUOUS = {  # symbol/word -> the currencies it can mean
    "¥": ("JPY", "CNY"), "￥": ("JPY", "CNY"),
    "$": ("USD", "SGD"), "DOLLAR": ("USD", "SGD"), "DOLLARS": ("USD", "SGD"),
}


@dataclass
class CurrencyResolution:
    code: str | None            # the code to convert from, when resolved
    status: str                 # "ok" | "confirm" | "unsupported"
    message: str = ""           # shown to the user for confirm/unsupported
    assumption: str = ""        # recorded when the city's currency decided an ambiguous symbol
    candidates: tuple = ()


def _key(raw: str) -> str:
    return re.sub(r"\s+", " ", raw.strip()).upper().replace("＄", "$")


def resolve_currency(raw: str, ds: Dataset) -> CurrencyResolution:
    k = _key(raw)
    local, display, city = ds.city.currency_code, ds.city.display_currency_code, ds.city.display_name
    if k in _AMBIGUOUS:
        cands = _AMBIGUOUS[k]
        if k in ("¥", "￥") and local in cands:
            return CurrencyResolution(local, "ok", assumption=f"'{raw.strip()}' can mean yen or yuan; read as {local} because the selected city is {city}.", candidates=cands)
        usable = [c for c in (local, display) if c]
        return CurrencyResolution(None, "confirm", candidates=cands,
                                  message=f"You wrote '{raw.strip()[:8]}', which can mean {' or '.join(cands)}. This trip is in {city} ({local}); "
                                          f"I can convert {local} or {display}. Which did you mean? Please restate the amount in {local} or {display}.")
    code = _UNAMBIGUOUS.get(k)
    if code is None and re.fullmatch(r"[A-Z]{3}", k):
        code = k  # some other ISO-style code: handled below as "no rate"
    if code is None:
        return CurrencyResolution(None, "unsupported", message=f"I do not recognise the currency '{raw.strip()[:8]}'. Please give the amount in {local} or {display}.")
    if code in (local, display):
        return CurrencyResolution(code, "ok")
    return CurrencyResolution(None, "unsupported",
                              message=f"This trip is in {city} ({local}). I have no sample rate for {code}, so I cannot convert it. Please give the amount in {local} or {display}.")


def to_local(amount: float, code: str, ds: Dataset) -> int:
    """Convert a resolved code (the city's local or display currency) to local integer units with the labelled SAMPLE rate."""
    if code == ds.city.currency_code:
        return int(round(amount))
    return int(round(amount / ds.city.sample_fx_to_display_currency))
