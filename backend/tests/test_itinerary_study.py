import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_quick_study_runs_and_keeps_its_invariants(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "scripts" / "run_itinerary_study.py"), "--quick", "--out", str(tmp_path)], check=True, capture_output=True)
    d = json.loads((tmp_path / "itinerary-study.json").read_text())
    assert set(d["cities"]) == {"tokyo", "singapore", "seoul", "kuala_lumpur"}
    for c in d["cities"].values():
        s = c["summary"]
        assert s["optimiser_infeasible_but_baseline_feasible"] == 0              # a baseline never finds a plan the optimiser cannot
        for k in ("input_order", "nearest_feasible", "optimiser"):
            a = s["arms"][k]
            assert a["feasible"] + a["no_plan"] + a["failed_validator"] == a["n"]  # every trip is accounted for
        for k in ("input_order", "nearest_feasible"):
            assert s["matched"][k]["score_gain"]["worse"] == 0                    # forced to the same sights, the optimiser's score is never worse
    assert "is not money spent" in (tmp_path / "itinerary-study.md").read_text()
