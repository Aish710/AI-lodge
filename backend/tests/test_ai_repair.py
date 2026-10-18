"""AI-assisted repair and AI-interpreted profiles: mock model only. The model chooses from a closed list; code resolves, derives flags, refuses, verifies and applies."""
import copy

import pytest
from fastapi.testclient import TestClient

from app.data.loader import load_all_city_datasets
from app.llm.client import LLMUnavailable, get_llm_client
from app.main import app
from app.schemas import LockedActivity, Preferences
from llm_mock import MockLLM

ALL = load_all_city_datasets()
TK, KL = ALL["tokyo"], ALL["kuala_lumpur"]
TH, KH = "hotel_lantern_asakusa", "hotel_klcc_lantern"
MOSQUE = "national_mosque_malaysia"


def r_out(*actions, keep=False, unsupported=(), unclear=()):
    full = []
    for a in actions:
        d = {"action": "set_pace", "attraction_name": None, "hotel_name": None, "minutes": None, "count": None, "pace": None, "direction": None, "reason": "because"}
        d.update(a)
        full.append(d)
    return {"actions": full, "keep_hotel_requested": keep, "unsupported": list(unsupported), "unclear": list(unclear)}


@pytest.fixture
def api():
    made = []

    def make(mock=None):
        app.dependency_overrides[get_llm_client] = lambda: mock
        c = TestClient(app)
        c.__enter__()
        made.append(c)
        return c
    yield make
    for c in made:
        c.__exit__(None, None, None)
    app.dependency_overrides.pop(get_llm_client, None)


def tokyo_cap(**over):
    return Preferences(days=1, must_visit=["senso_ji", "meiji_jingu", "shibuya_sky"], pace="relaxed", start_weekday=2, **over)


def kl_blocked():
    return Preferences(days=2, must_visit=[MOSQUE], start_weekday=2)


def propose(c, text, prefs, hotel, city="tokyo", keep=False):
    return c.post("/parse-repair", json={"city_id": city, "text": text, "preferences": prefs.model_dump(), "hotel_id": hotel, "keep_hotel": keep}).json()


def apply(c, prop, prefs, hotel, city="tokyo", keep=False, confirm=(), **over):
    body = {"city_id": city, "preferences": prefs.model_dump(), "hotel_id": hotel, "keep_hotel": keep, "base_fingerprint": prop["base_fingerprint"], "actions": prop["actions"], "confirmed_ids": list(confirm)}
    body.update(over)
    return c.post("/apply-repair", json=body)


def test_a_repair_is_proposed_verified_and_applied_only_after_the_person_applies_it(api):
    p = tokyo_cap()
    c = api(MockLLM([r_out({"action": "set_max_activities", "count": 3, "reason": "fits three must-visits"})]))
    j = propose(c, "I want all three, make it fit", p, TH)
    assert j["status"] == "ok" and j["executed"] is False and j["verification"]["state"] == "verified" and j["verification"]["verified"] is True
    a = j["actions"][0]
    assert (a["action"], a["expected_previous"], a["proposed"], a["requires_confirmation"]) == ("set_max_activities", None, 3, False)
    assert any("must-visits stay required" in u for u in j["unchanged"])
    r = apply(c, j, p, TH)
    assert r.status_code == 200 and r.json()["result"]["status"] == "feasible" and r.json()["new_preferences"]["max_activities_per_day"] == 3
    assert r.json()["feasibility_report"]["overall"] != "fail" and r.json()["fingerprint"]


def test_unknown_hours_repair_is_provisional_needs_individual_confirmation_and_stays_conditional(api):
    p = kl_blocked()
    c = api(MockLLM([r_out({"action": "allow_unknown_hours", "reason": "I need the mosque"})]))
    j = propose(c, "I really want the National Mosque, plan it provisionally", p, KH, "kuala_lumpur")
    a = j["actions"][0]
    assert a["requires_confirmation"] is True and a["hard_constraint"] is True and j["hard_changes"] and j["verification"]["state"] == "conditional" and j["verification"]["verified"] is False
    r = apply(c, j, p, KH, "kuala_lumpur")
    assert r.status_code == 422 and r.json()["error"]["code"] == "confirmation_required"
    r = apply(c, j, p, KH, "kuala_lumpur", confirm=[a["id"]])
    assert r.status_code == 200 and r.json()["feasibility_report"]["verification"] == "conditional" and r.json()["new_preferences"]["allow_unknown_hours"] is True


def test_a_kept_hotel_can_never_be_switched_by_a_repair(api):
    p = tokyo_cap()
    c = api(MockLLM([r_out({"action": "switch_hotel", "hotel_name": TK.hotels["hotel_harbour_odaiba"].name}, {"action": "set_max_activities", "count": 3})]))
    j = propose(c, "keep my hotel but make it work", p, TH, keep=True)
    assert [a["action"] for a in j["actions"]] == ["set_max_activities"] and any("keep your hotel" in x["why"].lower() for x in j["refused"])
    # even if a client forges a switch action the server refuses it at application time
    forged = copy.deepcopy(j)
    forged["actions"] = [{"id": "a1", "action": "switch_hotel", "target": TH, "target_label": "x", "expected_previous": TH, "proposed": "hotel_harbour_odaiba", "reason": "", "hard_constraint": False, "requires_confirmation": False}]
    r = apply(c, forged, p, TH, keep=True)
    assert r.status_code == 422 and r.json()["error"]["code"] == "hotel_locked"


def test_the_model_saying_keep_my_hotel_blocks_a_hotel_switch_even_when_the_lock_is_off(api):
    p = tokyo_cap()
    c = api(MockLLM([r_out({"action": "switch_hotel", "hotel_name": TK.hotels["hotel_harbour_odaiba"].name}, keep=True)]))
    j = propose(c, "keep my hotel", p, TH, keep=False)
    assert j["actions"] == [] and j["keep_hotel_inferred"] is True


def test_a_stale_proposal_is_refused(api):
    p = tokyo_cap()
    c = api(MockLLM([r_out({"action": "set_max_activities", "count": 3})]))
    j = propose(c, "fit all three", p, TH)
    changed = p.model_copy(update={"days": 2})
    r = apply(c, j, changed, TH)
    assert r.status_code == 409 and r.json()["error"]["code"] == "stale_proposal"
    r2 = apply(c, j, p, TH, base_fingerprint="0" * 16)
    assert r2.status_code == 409


def test_an_action_that_no_longer_matches_the_current_value_is_refused_even_with_a_matching_fingerprint(api):
    p = tokyo_cap()
    c = api(MockLLM([r_out({"action": "set_pace", "pace": "packed"})]))
    j = propose(c, "faster", p, TH)
    forged = copy.deepcopy(j)
    forged["actions"][0]["expected_previous"] = "balanced"          # time-of-check/time-of-use: the proposal claims the pace was balanced
    r = apply(c, forged, p, TH)
    assert r.status_code == 409 and r.json()["error"]["code"] == "stale_proposal"


def test_flags_are_derived_in_code_a_forged_action_cannot_lower_its_own_confirmation_requirement(api):
    p = Preferences(days=2, must_visit=["senso_ji", "shibuya_sky"], start_weekday=2)
    c = api(MockLLM([r_out({"action": "demote_must_visit", "attraction_name": "Senso-ji"})]))
    j = propose(c, "drop senso-ji from my must-visits", p, TH)
    assert j["actions"][0]["requires_confirmation"] is True and "gives" not in j["hard_changes"]
    forged = copy.deepcopy(j)
    forged["actions"][0]["requires_confirmation"] = False
    assert apply(c, forged, p, TH).json()["error"]["code"] == "confirmation_required"      # the confirmation rule is derived from the ACTION, not from the forged flag
    r = apply(c, forged, p, TH, confirm=[forged["actions"][0]["id"]])
    assert r.status_code == 422 and r.json()["error"]["code"] == "flags_mismatch"
    assert apply(c, j, p, TH).status_code == 422                     # and without the individual confirmation it is refused
    ok = apply(c, j, p, TH, confirm=[j["actions"][0]["id"]])
    assert ok.status_code == 200 and "senso_ji" not in ok.json()["new_preferences"]["must_visit"]


def test_removing_an_optional_sight_works_but_a_must_visit_cannot_be_removed_that_way(api):
    p = Preferences(days=2, must_visit=["senso_ji"], start_weekday=2)
    c = api(MockLLM([r_out({"action": "remove_optional", "attraction_name": "Senso-ji"}), r_out({"action": "remove_optional", "attraction_name": "Shibuya Sky"})]))
    j = propose(c, "remove senso-ji", p, TH)
    assert j["actions"] == [] and j["refused"] and "must-visit" in j["refused"][0]["why"]
    j2 = propose(c, "skip shibuya sky", p, TH)
    assert j2["actions"][0]["action"] == "remove_optional" and j2["actions"][0]["requires_confirmation"] is False


def test_a_locked_attraction_is_never_moved_or_removed_by_a_repair(api):
    p = Preferences(days=2, must_visit=["senso_ji"], start_weekday=2, locked=[LockedActivity(attraction_id="shibuya_sky", day=1, start_time="15:00")])
    c = api(MockLLM([r_out({"action": "remove_optional", "attraction_name": "Shibuya Sky"})]))
    j = propose(c, "skip shibuya sky", p, TH)
    assert j["actions"] == [] and "locked" in j["refused"][0]["why"].lower()


def test_names_and_fields_the_data_does_not_have_become_clarifications_never_actions(api):
    p = tokyo_cap()
    c = api(MockLLM([r_out({"action": "remove_optional", "attraction_name": "Atlantis Casino"}, {"action": "switch_hotel", "hotel_name": "Evil Palace"})]))
    j = propose(c, "remove atlantis and move to evil palace", p, TH)
    assert j["actions"] == [] and j["status"] == "needs_clarification" and j["unresolved_names"]
    bad = r_out({"action": "set_max_activities", "count": 3})
    bad["actions"][0]["opening_hours"] = "09:00-23:00"                     # a smuggled field
    c2 = api(MockLLM([bad, bad]))
    j2 = propose(c2, "fit them", p, TH)
    assert j2["actions"] == [] and "09:00" not in str(j2["actions"])


def test_out_of_range_numbers_are_refused_in_code(api):
    p = tokyo_cap()
    c = api(MockLLM([r_out({"action": "set_max_daily_travel", "minutes": 5}, {"action": "extend_day", "minutes": 0})]))
    j = propose(c, "limit travel to 5 minutes and extend zero", p, TH)
    assert j["actions"] == [] or all(a["proposed"] != 5 for a in j["actions"])
    assert j["refused"] or j["clarifications"]


def test_unsupported_requests_are_listed_not_acted_on(api):
    p = tokyo_cap()
    c = api(MockLLM([r_out({"action": "set_max_activities", "count": 3}, unsupported=["a quieter route"])]))
    j = propose(c, "fit them and make it quiet", p, TH)
    assert j["unsupported"] == ["a quieter route"] and len(j["actions"]) == 1


def test_a_failing_model_leaves_the_plan_alone_and_the_deterministic_repairs_available(api):
    p = tokyo_cap()
    c = api(MockLLM([LLMUnavailable("timeout")]))
    j = propose(c, "fix it", p, TH)
    assert j["status"] == "llm_unavailable" and j["actions"] == [] and j["executed"] is False
    o = c.post("/optimise", json={"preferences": p.model_dump(), "hotel_id": TH}).json()
    assert o["result"]["status"] == "infeasible" and o["result"]["alternatives"]          # the deterministic repair cards are unaffected
    c2 = api(None)
    assert propose(c2, "fix it", p, TH)["status"] == "llm_unavailable"


def test_a_repair_that_does_not_work_is_labelled_not_verified(api):
    p = Preferences(days=1, must_visit=["senso_ji", "meiji_jingu", "shibuya_sky"], pace="relaxed", start_weekday=2, max_daily_travel_minutes=20)
    c = api(MockLLM([r_out({"action": "set_pace", "pace": "packed"})]))
    j = propose(c, "pack it", p, TH)
    assert j["verification"]["verified"] is False and j["verification"]["state"] in ("infeasible", "blocked_missing_info")


def test_foreign_city_ids_in_an_applied_repair_are_refused(api):
    p = tokyo_cap()
    c = api(MockLLM([r_out({"action": "set_max_activities", "count": 3})]))
    j = propose(c, "fit them", p, TH)
    forged = copy.deepcopy(j)
    forged["actions"] = [{"id": "a1", "action": "remove_optional", "target": "gyeongbokgung", "target_label": "x", "expected_previous": "optional", "proposed": "skip", "reason": "", "hard_constraint": False, "requires_confirmation": False}]
    r = apply(c, forged, p, TH)
    assert r.status_code in (400, 409, 422) and r.json()["error"]["code"] in ("foreign_id", "wrong_city", "unknown_attraction", "city_mismatch")


# ---- profiles ---------------------------------------------------------------------------------------------------------------------------------------------
def profile_out(**over):
    d = {"tags": [], "max_activities": None, "max_daily_travel_minutes": None, "budget": None, "must_visit_names": [], "unsupported": [], "unclear": []}
    d.update(over)
    return d


def prof(c, text, mock_current=None, overrides=(), city="tokyo"):
    cur = {"pace": "balanced", "maxActivities": "", "maxDailyTravel": "", "valueOfTime": 1000}
    cur.update(mock_current or {})
    return c.post("/parse-profile", json={"city_id": city, "text": text, "current": cur, "user_overrides": list(overrides)}).json()


def test_profile_tags_become_labelled_inferred_settings_and_nothing_is_applied(api):
    c = api(MockLLM([profile_out(tags=["slow_pace", "pay_more_to_save_time"])]))
    j = prof(c, "I prefer a slow trip with lots of breaks, and I don't mind paying more if it saves time")
    assert j["executed"] is False and j["status"] == "ok"
    by = {s["field"]: s for s in j["settings"]}
    assert by["pace"]["proposed"] == "relaxed" and by["maxActivities"]["proposed"] == 2 and by["valueOfTime"]["proposed"] == 4000
    assert all(s["source"] == "inferred" and s["requires_confirmation"] for s in j["settings"])


def test_explicit_numbers_must_be_in_the_users_words_a_made_up_number_is_dropped(api):
    c = api(MockLLM([profile_out(max_activities=3), profile_out(max_activities=5)]))
    ok = prof(c, "at most 3 activities a day")
    assert [(s["field"], s["proposed"], s["source"]) for s in ok["settings"]] == [("maxActivities", 3, "explicit")]
    made_up = prof(c, "I want a relaxed trip")
    assert made_up["settings"] == [] and any("not written in your text" in x for x in made_up["clarifications"])


def test_limited_budget_without_an_amount_asks_a_question_and_invents_nothing(api):
    c = api(MockLLM([profile_out(tags=["limited_budget"], must_visit_names=["Senso-ji", "Shibuya Sky"])]))
    j = prof(c, "I have a limited budget but Senso-ji and Shibuya Sky are essential")
    assert j["questions"] and not any(s["field"] == "budget" for s in j["settings"])
    assert {s["target"] for s in j["settings"] if s["field"] == "must_visit"} == {"senso_ji", "shibuya_sky"}


def test_a_stated_budget_is_explicit_only_when_the_amount_is_in_the_text(api):
    c = api(MockLLM([profile_out(budget={"amount": 50000, "currency": "JPY", "strict": True}), profile_out(budget={"amount": 99999, "currency": "JPY", "strict": False})]))
    j = prof(c, "my budget is 50,000 yen")
    assert [(s["field"], s["proposed"], s["source"]) for s in j["settings"]] == [("budget", 50000, "explicit")]
    k = prof(c, "I have a small budget")
    assert not any(s["field"] == "budget" for s in k["settings"])


def test_a_setting_the_user_already_set_is_kept_unless_the_text_explicitly_asks(api):
    c = api(MockLLM([profile_out(tags=["slow_pace"]), profile_out(tags=["slow_pace"], max_activities=4)]))
    j = prof(c, "slow trip", {"pace": "packed"}, overrides=["pace"])
    pace = next(s for s in j["settings"] if s["field"] == "pace")
    assert pace["kept_yours"] is True
    k = prof(c, "slow trip, at most 4 activities", {"maxActivities": 6}, overrides=["maxActivities"])
    assert next(s for s in k["settings"] if s["field"] == "maxActivities")["kept_yours"] is False


def test_unsupported_preferences_are_listed_and_never_become_settings(api):
    c = api(MockLLM([profile_out(tags=["short_travel"], unsupported=["wheelchair accessible", "quiet streets"])]))
    j = prof(c, "no long travel, wheelchair accessible, quiet streets")
    assert j["unsupported"] == ["wheelchair accessible", "quiet streets"] and [s["field"] for s in j["settings"]] == ["maxDailyTravel"]


def test_profile_output_with_extra_fields_or_in_sample_mode_changes_nothing(api):
    bad = profile_out(tags=["slow_pace"])
    bad["hotel"] = "evil"
    c = api(MockLLM([bad, bad]))
    j = prof(c, "slow")
    assert j["settings"] == [] and j["executed"] is False
    assert prof(api(None), "slow")["status"] == "llm_unavailable"
