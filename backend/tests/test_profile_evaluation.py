import json
import subprocess
import sys
from pathlib import Path

from app.schemas import Preferences

ROOT = Path(__file__).resolve().parents[1]
PROFILES = json.loads((ROOT.parent / "frontend" / "src" / "lib" / "profiles.json").read_text())["profiles"]


def test_every_profile_value_is_accepted_by_the_request_schema():
    for p in PROFILES:
        kw = dict(days=2, pace=p["pace"], value_of_time_per_hour=round(1000 * p["votFactor"]))
        if p["maxActivities"] != "":
            kw["max_activities_per_day"] = p["maxActivities"]
        if p["maxDailyTravel"] != "":
            kw["max_daily_travel_minutes"] = p["maxDailyTravel"]
        Preferences(**kw)


def test_quick_profile_evaluation_runs_and_accounts_for_every_trip(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "scripts" / "run_profile_evaluation.py"), "--quick", "--out", str(tmp_path)], check=True, capture_output=True)
    d = json.loads((tmp_path / "profile-results.json").read_text())
    for c in d["cities"].values():
        for p in c["profiles"].values():
            assert p["feasible"] + p["infeasible_with_profile"] == p["comparable_trips"]
            assert p["same_plan_as_no_profile"] <= p["feasible"]
