"""The ONE place that prints amounts in server-built sentences. A sentence never hardcodes a currency: it asks for the selected city's own
code, so a Seoul sentence says "KRW 135,000"-style units and never "JPY". (Internal field names such as `true_cost_jpy` are historical:
they hold the city's local integer currency units.) Amounts keep the code next to the number so "yen" and "yuan" can never be confused."""
from app.data.loader import Dataset


def code(ds: Dataset) -> str:
    return ds.city.currency_code


def money(n: int | float, ds: Dataset) -> str:
    """'1,500 JPY' / '135,000 KRW': grouped digits, then the city's currency code."""
    return f"{int(round(n)):,} {code(ds)}"


def signed(n: int | float, ds: Dataset, unit: str | None = None) -> str:
    """'+2,413 JPY'. With `unit` (e.g. 'min') the unit replaces the currency."""
    return f"{int(round(n)):+,} {unit or code(ds)}"


def per_hour(n: int | float, ds: Dataset) -> str:
    """'1,000 JPY/h'."""
    return f"{n:,.0f} {code(ds)}/h"


def display_amount(local: int | float, ds: Dataset) -> str:
    """The labelled SAMPLE conversion into the display currency, e.g. 'about S$14 at the SAMPLE rate'."""
    value = local * ds.city.sample_fx_to_display_currency
    cur = ds.city.display_currency_code
    amount = f"S${value:,.0f}" if cur == "SGD" else f"{cur} {value:,.0f}"
    return f"about {amount} at the SAMPLE rate"


def missed_preference_penalty(ds: Dataset) -> int:
    """What leaving out one optional sight is charged in true cost: the value of THREE hours of time at the city's own default value of time.
    For Tokyo (1,000 JPY/h) this is exactly the old constant 3,000 JPY; for Seoul it is 45,000 KRW. A fixed 3,000 in every city's own currency
    was about 20 US dollars in Tokyo but about 2 in Seoul, which made the Seoul planner skip almost every sight."""
    return 3 * ds.city.default_value_of_time_per_hour
