"""Reproducible hotel-comparison run on the real (sample) dataset. No tuning, no LLM.

Run from backend/:  python scripts/run_hotel_comparison.py
Writes ../docs/hotel-comparison-results.md and ../docs/hotel-comparison-sample.json.
Every number in those files comes from this script's run on this machine.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402
from app.data.loader import load_dataset  # noqa: E402
from app.optimiser.hotel_compare import compare_hotels  # noqa: E402
from app.schemas import Preferences  # noqa: E402

DOCS = ROOT.parent / "docs"
EXTENDED_LIMIT = 120.0  # seconds, for the reported results; the default-limit run is reported separately
TRIPS = [
    ("Trip A: 2 days, Sat-Sun", Preferences(days=2, pace="balanced", must_visit=["senso_ji", "shibuya_sky"], start_weekday=5, value_of_time_per_hour=1000)),
    ("Trip B: 3 days, Wed-Fri", Preferences(days=3, pace="balanced", must_visit=["senso_ji", "meiji_jingu", "tokyo_national_museum"], start_weekday=2, value_of_time_per_hour=1000)),
    ("Trip C: 4 days, Thu-Sun", Preferences(days=4, pace="relaxed", must_visit=["ghibli_museum", "teamlab_planets", "tsukiji_outer_market", "shinjuku_gyoen"], start_weekday=3, value_of_time_per_hour=1000)),
]


def main():
    ds = load_dataset()
    hotels = list(ds.hotels)
    cheapest = min(hotels, key=lambda h: ds.hotels[h].nightly_rate)
    out = [
        "# Hotel comparison results (SAMPLE data)", "",
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by `backend/scripts/run_hotel_comparison.py`. "
        "Hotels are FICTIONAL; attraction data is approximate sample data; travel times and fares are ESTIMATES. Not live prices.", "",
        f"Settings: value of time 1,000 JPY/h unless stated; missed-preference penalty {config.MISSED_PREFERENCE_PENALTY_JPY} JPY per visitable "
        "nice-to-have not scheduled (a judgement call, not data); nights = days - 1; sensitivity range 0-3000 JPY/h. "
        f"Reported results use a {EXTENDED_LIMIT:.0f} s limit; the default API limit ({config.HOTEL_COMPARE_TIME_LIMIT_SECONDS:.0f} s) is reported per trip.", "",
        "Hotel nightly rates (JPY, fictional): " + ", ".join(f"{h.name} {h.nightly_rate:,}" for h in ds.hotels.values()), "",
    ]
    sample_json = None
    summary = []
    for title, prefs in TRIPS:
        default_run = compare_hotels(prefs, hotels, ds, include_sensitivity=True)
        c = compare_hotels(prefs, hotels, ds, include_sensitivity=True, time_limit=EXTENDED_LIMIT)
        if sample_json is None:
            sample_json = c.model_dump()
        out += [f"## {title}", "", f"Must-visits: {', '.join(prefs.must_visit)}. Pace: {prefs.pace}. Nights used: {c.nights_used} ({c.nights_source}).", "",
                "| Line (JPY) | " + " | ".join(r.hotel_name for r in c.results) + " |", "|---|" + "---|" * len(c.results)]
        rows = [("Rooms", lambda b: b.rooms_jpy), ("Admissions (known prices)", lambda b: b.admissions_jpy),
                ("Transport (estimated)", lambda b: b.transport_jpy), ("Travel minutes", lambda b: b.travel_minutes),
                ("Time cost", lambda b: b.time_cost_jpy), ("Missed-preference penalty", lambda b: b.missed_preferences.penalty_jpy),
                ("**True cost**", lambda b: b.true_cost_jpy)]
        for label, fn in rows:
            out.append(f"| {label} | " + " | ".join(f"{fn(r.breakdown):,}" if r.breakdown else "n/a" for r in c.results) + " |")
        out.append("| Missed (count) | " + " | ".join(str(r.breakdown.missed_preferences.count) if r.breakdown else "n/a" for r in c.results) + " |")
        out.append("| Solver status | " + " | ".join(f"{r.status} / {r.solver_status} / {r.runtime_seconds}s" for r in c.results) + " |")
        out += ["", f"- Cheapest by rate: **{ds.hotels[c.cheapest_by_rate].name}**; best by true cost: **{ds.hotels[c.best_by_true_cost].name if c.best_by_true_cost else 'none'}**; "
                f"rate winner differs from true winner: **{c.rate_winner_differs_from_true_winner}**.",
                f"- Insight: {c.insight}"]
        for w in c.warnings:
            out.append(f"- Warning: {w}")
        s = c.sensitivity
        out += [f"- Sensitivity: {s.flip_summary.rstrip('.')}. Approximate: {s.approximate}. Solves: {s.solves}, cache hits: {s.cache_hits}.", "",
                "| Value of time (JPY/h) | " + " | ".join(ds.hotels[h].name for h in hotels) + " | Winner |", "|---|" + "---|" * (len(hotels) + 1)]
        for g in s.grid:
            out.append(f"| {g.value_of_time_per_hour:,} | " + " | ".join(f"{g.true_cost_jpy.get(h, 0):,}" for h in hotels) + f" | {ds.hotels[g.winner].name} |")
        out += ["", f"- Default-limit run ({config.HOTEL_COMPARE_TIME_LIMIT_SECONDS:.0f} s): elapsed {default_run.elapsed_seconds}s, partial: {default_run.partial}, approximate: {default_run.approximate}.",
                f"- Extended run: elapsed {c.elapsed_seconds}s, partial: {c.partial}.", ""]
        cheap_wins = [g.value_of_time_per_hour for g in s.grid if g.winner == cheapest]
        summary.append((title, c.best_by_true_cost, c.rate_winner_differs_from_true_winner, cheap_wins, s.approximate, s.flips))
    out += ["## Does the cheapest-by-rate hotel ever lose?", "", f"Cheapest by rate: {ds.hotels[cheapest].name}.", ""]
    for title, best, differs, cheap_wins, approx, flips in summary:
        out.append(f"- {title}: best by true cost at 1,000 JPY/h = {ds.hotels[best].name if best else 'none'}; rate winner differs: {differs}; "
                   f"cheapest hotel wins at {len(cheap_wins)} of the grid points; flips: {[(f.from_winner, f.to_winner, f.value_of_time_per_hour) for f in flips] or 'none'}; approximate: {approx}.")
    (DOCS / "hotel-comparison-results.md").write_text("\n".join(out) + "\n")
    (DOCS / "hotel-comparison-sample.json").write_text(json.dumps(sample_json, indent=1) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
