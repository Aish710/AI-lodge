#!/usr/bin/env python3
"""Write frontend/src/lib/benefits.json from docs/itinerary-study.json (the generated itinerary study), so the Your Trip page can state the verified, per-city sample-data evidence
without typing any number by hand. Run after every itinerary study.  Usage: python scripts/make_benefit_facts.py [--root DIR]"""
import json
import sys
from pathlib import Path

root = Path(sys.argv[sys.argv.index("--root") + 1]) if "--root" in sys.argv else Path(__file__).resolve().parents[1]
d = json.loads((root / "docs" / "itinerary-study.json").read_text(encoding="utf-8"))
out = {"source": "docs/itinerary-study.json", "generated": d["meta"]["date"], "commit": d["meta"]["commit"], "cities": {}}
for c, v in d["cities"].items():
    s = v["summary"]
    a, m = s["arms"], s["matched"]["input_order"]
    out["cities"][c] = {
        "trips": v["n_trips"],
        "input_order_feasible": a["input_order"]["feasible"], "optimiser_feasible": a["optimiser"]["feasible"],
        "input_order_missed_a_must_where_optimiser_found_plan": a["input_order"]["missed_a_must_visit_where_optimiser_found_a_plan"],
        "matched_solved": m["matched_solved"], "minutes_better": m["minutes_saved"]["better"], "minutes_equal": m["minutes_saved"]["equal"], "minutes_worse": m["minutes_saved"]["worse"],
        "minutes_median": m["minutes_saved"].get("median"), "minutes_max": m["minutes_saved"].get("max"),
    }
(root / "frontend" / "src" / "lib" / "benefits.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
print("wrote frontend/src/lib/benefits.json")
