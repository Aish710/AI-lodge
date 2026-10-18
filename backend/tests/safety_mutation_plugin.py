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


def pytest_configure(config):
    name = os.environ.get("SAFETY_MUTATION")
    if not name:
        return
    if name not in MUTATIONS:
        raise SystemExit(f"unknown mutation {name}")
    MUTATIONS[name][0]()
