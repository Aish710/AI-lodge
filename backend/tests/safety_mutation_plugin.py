"""Safety mutation plugin. Loaded ONLY by scripts/run_safety_mutations.py (`-p safety_mutation_plugin`) with SAFETY_MUTATION=<name>.

It disables ONE safeguard in the running test process (a monkeypatch applied at start-up) so the runner can see which tests notice. It changes no file, no configuration and no
production default; with no SAFETY_MUTATION set it does nothing. Nothing weakened is ever committed.
"""
import os

MUTATIONS = {}


def mutation(name, why):
    def deco(fn):
        MUTATIONS[name] = (fn, why)
        return fn
    return deco


@mutation("leak_scrub_off", "model free text that quotes the system prompt or a secret is no longer scrubbed (runner)")
def _m1():
    import app.llm.runner as r
    r.scrub = lambda value, system="", secret="": (value, 0)


@mutation("leak_check_off", "an explanation that quotes the prompt or a key is no longer rejected (explain)")
def _m2():
    import app.llm.explain as e
    e.forbidden = lambda *a, **k: False


@mutation("claims_guard_off", "unsupported-claims word list (access, safety, quiet, ...) no longer rejects explanations")
def _m3():
    import app.llm.explain as e
    e.unsupported_claims = lambda *a, **k: []


@mutation("grounding_off", "numbers and names in an explanation are no longer checked against the computed facts")
def _m4():
    import app.llm.explain as e
    from app.llm.grounding import GroundingResult
    e.check_grounding = lambda *a, **k: GroundingResult(ok=True, checked=0, rejected_tokens=[])


@mutation("must_visit_confirmation_off", "removing a must-visit no longer needs the human's confirmation flag (replanner)")
def _m5():
    import app.optimiser.replan as rp
    orig = rp._apply
    rp._apply = lambda prefs, hotel, ops, ds, confirm: orig(prefs, hotel, ops, ds, True)


@mutation("untrusted_schedule_trusted", "a client-supplied schedule is used as is instead of being rebuilt and validated")
def _m6():
    import app.main as m
    m.rebuild_client_schedule = lambda prefs, current, ds, *a, **k: current


@mutation("no_valid_plan_guard_off", "the model may word an explanation of a plan that does not exist (main._explain_args)")
def _m7():
    import app.main as m
    m._explain_args = lambda client, request, ok: (client, request.state.llm_note)


@mutation("foreign_city_ids_accepted", "ids from another city are no longer rejected")
def _m8():
    import app.city_guard as g
    import app.main as m
    g.reject_foreign_ids = lambda *a, **k: None
    m.reject_foreign_ids = lambda *a, **k: None


@mutation("unknown_hours_assumed_open_by_default", "allow_unknown_hours defaults to True: a place with unknown hours is silently assumed open")
def _m9():
    from app.schemas import Preferences
    Preferences.model_fields["allow_unknown_hours"].default = True
    Preferences.model_rebuild(force=True)


@mutation("conflict_category_wrong", "missing-information conflicts are reported as known-constraint conflicts (UI would say 'impossible')")
def _m10():
    import app.schemas as s
    s.MISSING_INFORMATION_CODES = frozenset()


@mutation("alternatives_validator_gate_rejects_all", "the independent-validator gate on repair suggestions rejects everything (shows suggestions really pass through that gate)")
def _m11():
    import sys

    import app.validator.feasibility_report as fr
    orig = fr.build_report

    def gate(r, ds, p, h, *a, **k):
        rep = orig(r, ds, p, h, *a, **k)
        if sys._getframe(1).f_code.co_name == "probe":          # only the call made by solver._alternatives
            rep.overall = "fail"
        return rep
    fr.build_report = gate


@mutation("repair_expected_previous_unchecked", "an applied repair no longer checks that each action's expected previous value still holds (stale / time-of-check-time-of-use)")
def _m12():
    import app.repair as r

    class Anything:
        def __eq__(self, other):
            return True

        def __ne__(self, other):
            return False
    r.current_value = lambda *a, **k: Anything()


@mutation("repair_hotel_lock_ignored", "a repair may switch a hotel the person asked to keep")
def _m13():
    import app.repair as r
    orig = r._check
    r._check = lambda a, p, h, keep, ds: orig(a, p, h, False, ds)


@mutation("repair_confirmation_not_required", "apply-repair no longer demands the person's individual confirmation for hard-constraint actions")
def _m14():
    import app.main as m
    m.CONFIRMED = frozenset()


@mutation("repair_flags_not_derived", "confirmation and hard-constraint flags are no longer derived from the action (a forged or model-set flag would be trusted)")
def _m15():
    import app.repair as r
    r.CONFIRMED = frozenset()
    r.HARD = frozenset()


@mutation("repair_stale_fingerprint_unchecked", "an applied repair is no longer tied to the plan it was proposed for")
def _m16():
    import app.main as m
    import app.repair as r
    from types import SimpleNamespace
    m.base_fingerprint = lambda *a, **k: "ANY"
    orig = m.ApplyRepairRequest.model_validate
    # every proposal made while this mutation is active carries the same constant, so the check always passes
    r.base_fingerprint = lambda *a, **k: "ANY"
    import app.llm.repair as lr
    lr.base_fingerprint = lambda *a, **k: "ANY"


@mutation("style_numbers_not_grounded", "a number the model puts in a travel-style tag is accepted even if the user never wrote it")
def _m17():
    import app.llm.profile as pr
    pr._digits = lambda text: set(range(0, 100000))


@mutation("repair_reason_unfiltered", "the model's free-text reason (possible fabricated saving) is shown as written")
def _m18():
    import app.llm.repair as lr
    lr._clean_reason = lambda reason: reason


@mutation("copilot_schedule_rebuild_off", "copilot trusts supplied money and plan validity instead of rebuilding the schedule")
def _m19():
    import app.main as m
    m.rebuild_client_schedule = lambda prefs, current, ds, *a, **k: current


@mutation("copilot_fingerprint_unchecked", "copilot accepts a question attached to a stale scenario")
def _m20():
    import app.main as m
    from app.fingerprint import plan_fingerprint as original
    m.plan_fingerprint = lambda *a, **k: "0" * 16


@mutation("style_tension_unchecked", "contradictory style tags silently resolve by order instead of asking")
def _m21():
    import app.llm.profile as p
    original = p.call_json
    def no_tension(*a, **kw):
        out = original(*a, **kw)
        if out.parsed and "many_sights" in out.parsed.tags:
            out.parsed.tags = [t for t in out.parsed.tags if t != "many_sights"]
        if out.parsed and "save_money" in out.parsed.tags:
            out.parsed.tags = [t for t in out.parsed.tags if t != "save_money"]
        return out
    p.call_json = no_tension


def pytest_configure(config):
    name = os.environ.get("SAFETY_MUTATION")
    if not name:
        return
    if name not in MUTATIONS:
        raise SystemExit(f"unknown mutation {name}")
    MUTATIONS[name][0]()
