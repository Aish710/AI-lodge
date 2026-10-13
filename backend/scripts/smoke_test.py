"""Smoke test against a running server (local or live). Standard library only; works in sample mode (no key needed).

Usage:  python backend/scripts/smoke_test.py https://your-service.onrender.com
Prints PASS/FAIL per check; exits non-zero if anything fails. Makes about 10 requests, well inside the default rate limits.
A free host may take about a minute to wake up: the first call waits up to 150 s.
"""
import json
import sys
import time
import urllib.error
import urllib.request

PREFS = {"days": 2, "budget": None, "strict_budget": False, "pace": "balanced", "interests": [], "must_visit": ["senso_ji", "shibuya_sky"],
         "day_start": "09:00", "day_end": "19:00", "value_of_time_per_hour": 1000, "max_walking_minutes_per_day": 90, "start_weekday": 2,
         "allow_unknown_hours": False, "skip": ["teamlab_planets"], "nights": None, "locked": []}
HOTELS = ["hotel_lantern_asakusa", "hotel_harbour_odaiba"]
results: list[tuple[str, bool, str]] = []


def call(base, method, path, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}"), dict(r.headers)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw), dict(e.headers)
        except ValueError:
            return e.code, {"raw": raw[:200].decode("latin-1")}, dict(e.headers)


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))


def main(base):
    base = base.rstrip("/")
    t0 = time.time()
    health = None
    while time.time() - t0 < 150:
        try:
            s, health, _ = call(base, "GET", "/health", timeout=30)
            if s == 200:
                break
        except Exception:
            pass
        print("waiting for the service to wake up ...")
        time.sleep(5)
    if not health or health.get("status") != "ok":
        check("GET /health reachable", False, "no healthy response within 150 s")
        return summary()
    print(f"service answered after {time.time() - t0:.1f} s")
    check("GET /health", health.get("status") == "ok" and health.get("llm_mode") in ("llm", "sample"), str(health))
    print(f"      mode: {health.get('llm_mode')} (configured={health.get('llm_configured')}, limit_reached={health.get('llm_limit_reached')})")

    s, j, h = call(base, "GET", "/data/summary")
    check("GET /data/summary (sample data disclosed)", s == 200 and j["counts"]["attractions"] == 12 and j["data_quality"]["verified_records"] == 0 and "Sample data" in j["disclaimer"], str(j)[:150])
    check("security headers present", h.get("X-Content-Type-Options", h.get("x-content-type-options")) == "nosniff" and (h.get("X-Request-ID") or h.get("x-request-id")))

    s, j, _ = call(base, "POST", "/optimise", {"preferences": PREFS, "hotel_id": HOTELS[0]})
    ok = s == 200 and j["result"]["status"] == "feasible" and j["feasibility_report"]["overall"] in ("pass", "pass_with_warnings")
    check("POST /optimise (feasible, validator passes)", ok, f"{s} {str(j)[:150]}")
    schedule = j.get("result") if ok else None

    s, j, _ = call(base, "POST", "/compare-hotels", {"preferences": PREFS, "hotel_ids": HOTELS})
    check("POST /compare-hotels (winner by true cost)", s == 200 and j.get("best_by_true_cost") in HOTELS and j["nights_used"] == 1, f"{s} {str(j)[:150]}")

    if schedule:
        s, j, _ = call(base, "POST", "/replan", {"preferences": PREFS, "current_result": schedule, "operations": [
            {"op": "lock", "attraction_id": "senso_ji", "day": 1, "start_time": "14:00"}]})
        placed = [x for d in j.get("schedule", {}).get("days", []) for x in d["stops"] if x["attraction_id"] == "senso_ji"] if s == 200 else []
        check("POST /replan (lock honoured, diff present)", s == 200 and j["status"] == "applied" and placed and placed[0]["start"] == "14:00" and j["diff"] is not None, f"{s} {str(j)[:150]}")
        s, j, _ = call(base, "POST", "/replan", {"preferences": PREFS, "current_result": schedule, "operations": [{"op": "remove", "attraction_id": "senso_ji"}]})
        check("POST /replan rejects silent must-visit removal (422)", s == 422 and j["error"]["code"] == "must_visit_removal_not_confirmed", f"{s} {str(j)[:150]}")
    else:
        check("POST /replan (skipped: no schedule from /optimise)", False)

    bad = dict(PREFS, days=1, pace="packed", day_end="13:00", must_visit=["tokyo_national_museum", "senso_ji", "tokyo_skytree"], skip=[])
    s, j, _ = call(base, "POST", "/optimise", {"preferences": bad, "hotel_id": HOTELS[0]})
    check("deliberately infeasible request -> conflicts, not an error page",
          s == 200 and j["result"]["status"] == "infeasible" and j["result"]["conflicts"] and j["feasibility_report"]["overall"] == "fail", f"{s} {str(j)[:150]}")

    s, j, _ = call(base, "POST", "/parse", {"text": "3 days in Tokyo"})
    check("POST /parse works in sample or llm mode (never a 5xx)", s == 200 and j["status"] in ("llm_unavailable", "ok", "needs_clarification"), f"{s} {str(j)[:150]}")
    s, j, _ = call(base, "POST", "/optimise", {"preferences": PREFS, "hotel_id": "x", "surprise": 1})
    check("unknown field -> clean 422 error format", s == 422 and j["error"]["code"] == "validation_error", f"{s} {str(j)[:150]}")
    return summary()


def summary():
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
