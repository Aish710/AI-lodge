"""Writes docs/replan-samples.json: three full ReplanResult examples (SAMPLE data).
(a) remove + lock, (b) hotel switch, (c) infeasible replan (original plan returned unchanged).
Run from backend/:  python scripts/make_replan_samples.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402
from app.data.loader import load_dataset  # noqa: E402
from app.optimiser.replan import ChangeBudgetOp, LockOp, RemoveOp, SwitchHotelOp, replan  # noqa: E402
from app.optimiser.solver import ObjectiveSpec, solve  # noqa: E402
from app.schemas import Preferences  # noqa: E402

ds = load_dataset()
ASA = "hotel_lantern_asakusa"
prefs = Preferences(days=2, must_visit=["senso_ji", "shibuya_sky"], start_weekday=2, skip=["teamlab_planets"])
cur = solve(prefs, ASA, ds, with_alternatives=False, objective=ObjectiveSpec("true_cost", 1000, config.MISSED_PREFERENCE_PENALTY_JPY))
victim = next(s.attraction_id for d in cur.days for s in d.stops if s.attraction_id not in prefs.must_visit)
samples = {
    "a_remove_and_lock": replan(prefs, cur, [RemoveOp(op="remove", attraction_id=victim),
                                             LockOp(op="lock", attraction_id="senso_ji", day=1, start_time="14:00")], ds),
    "b_switch_hotel": replan(prefs, cur, [SwitchHotelOp(op="switch_hotel", hotel_id="hotel_harbour_odaiba")], ds),
    "c_infeasible_strict_budget": replan(prefs, cur, [ChangeBudgetOp(op="change_budget", budget=1000, strict=True)], ds),
}
out = {k: json.loads(v.model_dump_json()) for k, v in samples.items()}
out["_original_plan"] = json.loads(cur.model_dump_json())
(ROOT.parent / "docs" / "replan-samples.json").write_text(json.dumps(out, indent=1) + "\n")
for k, v in samples.items():
    print(k, v.status, "|", v.summary)
