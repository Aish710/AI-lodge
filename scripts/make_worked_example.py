"""Write docs/worked-example.md from REAL /compare-hotels output (the real app, sample mode, no model) for each city's pinned example trip
(frontend/src/lib/examples.json): the cheapest-rate hotel beside the best true-cost hotel, rooms, admissions, transport, travel time and true cost, a plain statement of
whether the winner changes, and how often that happened in the measured evaluation. Every figure is read from the API response or from the evaluation files; nothing is typed in.
The examples were chosen to show the trade-off. They are NOT representative.   Usage (from backend/, so the backend's own virtual environment is used):  .venv/bin/python ../scripts/make_worked_example.py [--out FILE]"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

EXAMPLES = REPO / "frontend" / "src" / "lib" / "examples.json"
ORDER = ["tokyo", "singapore", "seoul", "kuala_lumpur"]


def request_for(example: dict) -> dict:
    """The same request the app sends for the pinned example (mirrors frontend/src/lib/prefs.js buildPreferences for a budget-free example)."""
    f = example["form"]
    wl = example["wishlist"]
    prefs = dict(days=f["days"], budget=None, strict_budget=False, pace=f["pace"], interests=[], must_visit=[k for k, v in wl.items() if v == "must"],
                 skip=[k for k, v in wl.items() if v == "skip"], day_start=f["dayStart"], day_end=f["dayEnd"], value_of_time_per_hour=f["valueOfTime"],
                 max_walking_minutes_per_day=90, start_weekday=f["startWeekday"], allow_unknown_hours=False)
    return {"city_id": example["city_id"], "preferences": prefs, "hotel_ids": example["hotel_ids"], "include_sensitivity": False, "explain": False}


def money(v: int, cur: str) -> str:
    return f"{v:,} {cur}"


def frequency(city: str, ev: dict, cev: dict) -> str:
    if city == "tokyo":
        h = ev["metrics"]["hotel_value"]["vots"]["1000"]
        return (f"In the measured evaluation (docs/eval-results.json, {ev['metrics']['n_trips']} seeded synthetic trips), the lowest-rate hotel was not the best by true cost in "
                f"{h['cheapest_by_rate_not_best']} of {h['n_eligible']} trips where all three hotels were feasible, at the default value of time (1,000 JPY an hour).")
    h = cev["cities"][city]["metrics"]["hotel_value"]["vots"]["1000"]
    return (f"In the city evaluation (docs/city-eval-results.json, {cev['cities'][city]['metrics']['n_trips']} seeded synthetic trips, reported separately and never pooled), the lowest-rate hotel was not the best "
            f"by true cost in {h['cheapest_by_rate_not_best']} of {h['n_eligible']} eligible trips at the middle tested value of time (1000 local units an hour; the same number in every currency, so it is not a like-for-like value of time across cities).")


def section(city: str, example: dict, resp: dict, ev: dict, cev: dict) -> list[str]:
    cur = resp["city"]["currency_code"] if isinstance(resp.get("city"), dict) and resp["city"].get("currency_code") else ""
    rows = {r["hotel_id"]: r for r in resp["results"] if r["feasible"]}
    cheapest, best = resp["cheapest_by_rate"], resp["best_by_true_cost"]
    must = ", ".join(k.replace("_", " ") for k, v in example["wishlist"].items() if v == "must")
    out = [f"## {resp['city']['display_name'] if isinstance(resp.get('city'), dict) and resp['city'].get('display_name') else city.title()}", "",
           f"Example trip: {example['form']['days']} days, must-see places: {must}, an example value of time of {money(example['form']['valueOfTime'], cur)} an hour (chosen to illustrate the trade-off, not a typical value). "
           f"All amounts are in {cur}; hotels are made up; travel times and fares are estimates.", "",
           "| Hotel | Rate per night | Rooms | Admissions | Transport (estimated) | Travel time | Value of that time | Missed-sights charge | True cost |", "|---|---|---|---|---|---|---|---|---|"]
    for hid, r in rows.items():
        b = r["breakdown"]
        tag = " (cheapest rate)" if hid == cheapest else ""
        tag += " (best by true cost)" if hid == best else ""
        out.append(f"| {r['hotel_name']}{tag} | {money(r['nightly_rate_jpy'], cur)} | {money(b['rooms_jpy'], cur)} | {money(b['admissions_jpy'], cur)} | {money(b['transport_jpy'], cur)} | "
                   f"{b['travel_hours']} h | {money(b['time_cost_jpy'], cur)} | {money(b['missed_preferences']['penalty_jpy'], cur)} | {money(b['true_cost_jpy'], cur)} |")
    out.append("")
    if resp["rate_winner_differs_from_true_winner"]:
        c, b = rows[cheapest], rows[best]
        d = c["breakdown"]["true_cost_jpy"] - b["breakdown"]["true_cost_jpy"]
        dh = c["breakdown"]["travel_hours"] - b["breakdown"]["travel_hours"]
        df = c["breakdown"]["transport_jpy"] - b["breakdown"]["transport_jpy"]
        dm = c["breakdown"]["missed_preferences"]["count"] - b["breakdown"]["missed_preferences"]["count"]
        parts = [f"{dh:.2f} h less travel" if dh >= 0 else f"{-dh:.2f} h more travel",
                 f"{money(abs(df), cur)} {'less' if df >= 0 else 'more'} in estimated fares"]
        if dm > 0:
            parts.append(f"{dm} fewer of the optional sights left out (each missed sight is charged in the true cost)")
        out.append(f"**The winner changes.** {b['hotel_name']} is best by true cost, {money(d, cur)} cheaper overall than {c['hotel_name']}, the lowest-rate hotel. It costs more per night; over this trip it needs "
                   + ", ".join(parts) + ".")
    else:
        out.append(f"**The winner does not change.** {rows[best]['hotel_name']} is both the lowest-rate hotel and the best by true cost for this trip, so here the arithmetic confirms the obvious choice.")
    out += ["", frequency(city, ev, cev), ""]
    return out


def build() -> str:
    ex = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    ev = json.loads((REPO / "docs" / "eval-results.json").read_text(encoding="utf-8"))
    cev = json.loads((REPO / "docs" / "city-eval-results.json").read_text(encoding="utf-8"))
    try:
        git = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        git = "unknown"
    out = ["# Worked examples (from real output)", "",
           f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by `scripts/make_worked_example.py` at git `{git}`. Each table is the real `/compare-hotels` answer of the app (sample mode, no language model) for the city's pinned example trip in `frontend/src/lib/examples.json`.", "",
           "**These example trips were chosen to show the trade-off. They are not representative.** Where the winner changes (Tokyo, Seoul) it is because the example uses a high value of time; where it does not (Singapore, Kuala Lumpur) the arithmetic simply confirms the cheapest rate. "
           "The measured frequency under each example is the honest picture, and it differs by city: how often the lowest-rate hotel is not the best is stated under each one. Sample data, made-up hotels, estimated travel times and fares.", ""]
    with TestClient(app) as c:
        for city in ORDER:
            example = ex[city]["valid"]
            r = c.post("/compare-hotels", json=request_for(example))
            assert r.status_code == 200, (city, r.text[:200])
            out += section(city, example, r.json(), ev, cev)
    return "\n".join(out)


if __name__ == "__main__":
    args = sys.argv[1:]
    path = Path(args[args.index("--out") + 1]) if "--out" in args else REPO / "docs" / "worked-example.md"
    path.write_text(build(), encoding="utf-8")
    print(f"wrote {path}")
