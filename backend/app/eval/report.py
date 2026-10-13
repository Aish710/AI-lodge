"""Markdown rendering of the evaluation. Every number is read from the metrics / per-trip dicts; nothing is typed in by hand.
Rounding follows claims.py: values that favour the product round down, values that disfavour it round up."""
from app.eval.claims import down, up


def table(headers: list[str], rows: list[list]) -> list[str]:
    return ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows] + [""]


def stats(d: dict, nd: int = 1, favourable: bool = True, unit: str = "") -> str:
    if not d["n"]:
        return "n/a (N=0)"
    f = down if favourable else up
    return f"mean {f(d['mean'], nd)}{unit}, median {f(d['median'], nd)}{unit}, min {f(d['min'], nd)}{unit}, max {f(d['max'], nd)}{unit} (N={d['n']})"


def _reasons(d: dict) -> str:
    return ", ".join(f"{v} x {k.replace('_', ' ')}" for k, v in sorted(d.items())) or "none"


def _scenario_section(results) -> list[str]:
    n_pass = sum(r.passed for r in results)
    out = ["## The 15 scenarios", "",
           f"{n_pass} of {len(results)} PASS. The definitions live in `backend/app/eval/scenarios.py` and are shared with `backend/tests/test_evaluation.py`. "
           "Rows marked **mocked LLM: verifies the pipeline, not the model** use a scripted stand-in for the model; no real model is called anywhere in this evaluation.", ""]
    rows = [[r.num, r.category, r.name, r.expected, "PASS" if r.passed else "**FAIL**", r.observed + (" *(mocked LLM: verifies the pipeline, not the model)*" if r.mocked_llm else "")] for r in results]
    return out + table(["#", "Category", "Scenario", "Expected", "Result", "Observed"], rows)


def _generated_section(m: dict, seed: int, n: int) -> list[str]:
    g = m["generation"]
    out = ["## Generated trips", "",
           f"{n} seeded trips (seed {seed}, file `docs/eval-scenarios.json`): 2-4 days, 3-9 of the 12 sample attractions in random input order, 0-3 must-visits, "
           "random start weekday, a mix of no / soft / strict budgets (some deliberately tight), each of the 3 fictional hotels as the base in turn, balanced pace.", ""]
    rows = [["Trips", n], ["Hotels as base", _reasons(g["by_hotel"])], ["With at least one must-visit", g["with_must_visits"]],
            ["Strict budget (of which tight, factor < 0.7)", f"{g['strict_budget']} ({g['tight_strict_budget']})"],
            [f"Infeasible (solver reported conflicts), N={n}", f"{g['infeasible']} ({up(100 * g['infeasible'] / n) if n else 'n/a'}%)"],
            ["Infeasible, by conflict type (a trip can have several)", _reasons(g["infeasible_by_code"])],
            [f"Trivially easy (all visitable sights placed with at least one spare day of capacity, no strict budget), N={n}", g["trivially_easy"]],
            ["Comparable to the input-order baseline (same attractions scheduled)", m["travel"]["naive"]["n_comparable"]],
            ["Comparable to the nearest-neighbour baseline", m["travel"]["nn"]["n_comparable"]]]
    return out + table(["Item", "Count"], rows)


def _pooled_phrase(percent) -> str:
    if percent is None:
        return ""
    return f" ({down(percent)}% less)" if percent >= 0 else f" ({up(-percent)}% MORE)"


def _travel_section(m: dict) -> list[str]:
    out = ["## A. Travel time against two baselines", "",
           "Like-for-like rule: a trip counts only if the solver and that baseline scheduled exactly the same set of attractions. "
           "Reduction = baseline minutes - solver minutes (positive = the solver travels less); percent is relative to the baseline. "
           "The two baselines are reported separately and never merged. Travel minutes include the hotel legs.", ""]
    for key, title in (("naive", "Input-order baseline (Phase 2 naive: attractions in the user's listed order, filled day by day)"),
                       ("nn", "Nearest-neighbour baseline (from the hotel, always the nearest feasible unvisited attraction)")):
        c = m["travel"][key]
        out += [f"### {title}", "",
                f"Comparable trips: **{c['n_comparable']}** of {c['n_trips']}. Excluded: {c['excluded']['n']} ({_reasons(c['excluded']['reasons'])}).", ""]
        if c["n_comparable"]:
            pooled = c["pooled"]
            out += table(["Measure", "Value"], [
                ["Travel minutes saved per trip", stats(c["minutes_reduction"])], ["Percent reduction per trip", stats(c["percent_reduction"], unit="%")],
                ["Solver better / equal / worse", f"{c['better']} / {c['equal']} / {c['worse']} of {c['n_comparable']}"],
                ["Pooled minutes (solver vs baseline)", f"{pooled['solver_minutes']} vs {pooled['baseline_minutes']}" + _pooled_phrase(pooled["percent"])]])
            out += ["By how scattered the baseline route is (terciles of the baseline's own travel minutes; groups are small, and grouping by the denominator "
                    "partly builds in a pattern, so read this as a description, not a finding):", ""]
            out += table(["Group", "N", "Baseline minutes range", "Percent reduction", "Better / equal / worse"],
                         [[t["group"], t["n"], f"{t['baseline_minutes_range'][0]}-{t['baseline_minutes_range'][1]}", stats(t["percent_reduction"], unit="%"),
                           f"{t['better']} / {t['equal']} / {t['worse']}"] for t in c["terciles"]])
    p = m["placement"]
    out += ["### Placement rates (what each method managed to schedule)", "",
            f"Over the {p['n_trips']} trips where the solver produced a plan; {p['requested']} attractions requested in total, {p['visitable']} of them visitable at all "
            "(open on some trip day with known hours, long enough within the day window). A baseline that drops sights is not comparable on travel time. "
            "By design the product objective charges a fixed penalty for each skipped optional sight (config.MISSED_PREFERENCE_PENALTY_JPY) and skips one when visiting it would cost more than that in travel time at the trip's "
            "value of time, fares and admission; the baselines have no such trade-off, which is why they can schedule more sights and why many trips are not like-for-like.", ""]
    out += table(["Method", "Scheduled", "of requested", "of visitable"], [[k, p[k]["placed"], f"{down(100 * p[k]['placed'] / p['requested'])}%" if p["requested"] else "n/a",
                                                                         f"{down(100 * p[k]['placed'] / p['visitable'])}%" if p["visitable"] else "n/a"]
                                                                        for k in ("solver", "naive", "nn")])
    return out


def _secondary_section(m: dict) -> list[str]:
    sec = m.get("secondary_objectives")
    if not sec:
        return []
    out = ["## A2. Secondary analysis (post-hoc): the Phase 2 weighted objective", "",
           "**Added AFTER the headline result in section A was seen. Not what the product runs, and not used for any headline claim.** "
           "Section A uses the objective that `POST /optimise`, `/compare-hotels` and `/replan` run (true cost). The older Phase 2 weighted objective is still the default of "
           "`solve()` when it is called directly, but no API route uses it. It includes a pace-balance term (config.W_PACE) that spreads stops evenly over the days, and extra days mean extra hotel round trips. "
           "The same trips are solved with that objective, and again with only that one weight set to 0 (a diagnostic), and compared with the same baselines under the same like-for-like rule.", ""]
    labels = {"phase2_default": "Phase 2 weighted objective", "phase2_default_pace_balance_off": "Phase 2 weighted objective, pace balance off (diagnostic)"}
    rows = []
    for name, v in sec["variants"].items():
        for key, label in (("naive", "Input-order baseline"), ("nn", "Nearest-neighbour baseline")):
            c = v[key]
            rows.append([labels.get(name, name), label, f"{c['n_comparable']} of {c['n_trips']}", stats(c["percent_reduction"], unit="%"), f"{c['better']} / {c['equal']} / {c['worse']}",
                         f"{c['pooled']['solver_minutes']} vs {c['pooled']['baseline_minutes']}" + _pooled_phrase(c["pooled"]["percent"])])
    out += table(["Solver setting", "Compared with", "Comparable trips", "Percent reduction per trip", "Better / equal / worse", "Pooled minutes (solver vs baseline)"], rows)
    sp = sec["stops_per_day_spread"]
    names = {"solver_product_objective": "Solver (product objective, section A)", "solver_phase2_default": "Solver (Phase 2 weighted objective)",
             "solver_phase2_default_pace_balance_off": "Solver (Phase 2 objective, pace balance off)", "input_order": "Input-order baseline", "nearest_neighbour": "Nearest-neighbour baseline"}
    out += ["How evenly each method loads the days (busiest day's stops minus quietest day's stops, mean over trips where the product solver produced a plan):", ""]
    out += table(["Method", "N trips", "Mean spread"], [[names.get(k, k), v["n"], up(v["mean_busiest_minus_quietest_day"], 2) if v["n"] else "n/a"] for k, v in sp.items()])
    return out


def _validation_section(m: dict) -> list[str]:
    v = m["validation"]
    out = ["## B. Constraint satisfaction (independent validator on every itinerary)", "",
           "The validator re-checks overlaps, hours, travel gaps, day window, must-visits, locks, pace cap, skips and budget from the dataset, without importing the optimiser. "
           "A baseline that could not place a must-visit still holds a partial plan; that plan is validated as it stands, so it FAILS the must-visit check. "
           "`no plan` = the solver reported the request infeasible, so there is nothing to validate.", ""]
    out += table(["Method", "N trips", "pass", "pass with warnings", "fail", "no plan", "fail for a reason beyond a missing must-visit", "failed checks (count of plans)"],
                 [[k, v[k]["n_trips"], v[k]["pass"], v[k]["pass_with_warnings"], v[k]["fail"], v[k]["no_plan"], v[k]["fail_hard_constraint_beyond_missing_must_visit"], _reasons(v[k]["failed_checks"])]
                  for k in ("solver", "naive", "nn")])
    return out


def _budget_section(m: dict) -> list[str]:
    b = m["budget"]
    out = ["## C. Budget compliance (strict budgets only)", "",
           f"Strict-budget trips: {b['n_strict_trips']}. A method's plan counts if its status is feasible; the budget covers attraction admissions + estimated transport.", ""]
    return out + table(["Method", "Feasible plans", "Within budget", "Trips with no feasible plan"], [[k, b[k]["feasible_plans"], b[k]["within_budget"], b[k]["no_feasible_plan"]] for k in ("solver", "naive", "nn")])


def _must_section(m: dict) -> list[str]:
    mv = m["must_visit"]
    out = ["## D. Must-visit handling", "", f"Trips with at least one must-visit: {mv['n_trips_with_must']}.", ""]
    out += table(["Method", "All must-visits placed", "Reported infeasible", "Silently dropped a must-visit"], [[k, mv[k]["all_placed"], mv[k]["reported_infeasible"], mv[k]["silently_dropped"]] for k in ("solver", "naive", "nn")])
    a = mv["infeasible_audit"]
    out += ["### Are the solver's infeasibility reports correct?", "",
            "Each reported conflict is re-derived from the dataset in `backend/app/eval/independent.py` (which imports nothing from the optimiser), and an exhaustive search over day assignments "
            "and visiting orders checks that no must-visit schedule exists. 'Not checkable' = the code cannot be rechecked independently (e.g. a solver time-out).", "",
            f"Infeasible trips: {a['n_infeasible']}. Every stated conflict confirmed: {a['all_stated_conflicts_confirmed']}. Exhaustive search agrees no schedule exists: {a['brute_force_agrees_no_schedule']}; "
            f"found a schedule the solver missed: {a['brute_force_found_a_schedule']}; not decided: {a['brute_force_not_decided']}.", ""]
    if a["by_code"]:
        out += table(["Conflict code", "Reported", "Confirmed", "Contradicted", "Not checkable"], [[c, e["n"], e["confirmed"], e["contradicted"], e["not_checkable"]] for c, e in sorted(a["by_code"].items())])
    return out


def _hotel_section(m: dict) -> list[str]:
    h = m["hotel_value"]
    out = ["## E. Hotel value (the signature claim)", "",
           "**Hotels and rates are FICTIONAL and were tuned for the demo in Phase 4. This measures the model's behaviour on sample data, not real hotel markets.** "
           "True cost = rooms + admissions + estimated transport + travel time x value of time + missed-preference penalty. Only trips where all three hotels were feasible are counted. "
           "1,000 JPY/h is the product default.", ""]
    rows = []
    for v, e in h["vots"].items():
        n = e["n_eligible"]
        rows.append([f"{int(v):,}", e["n_trips"], n, f"{e['cheapest_by_rate_not_best']} ({down(100 * e['cheapest_by_rate_not_best'] / n)}%)" if n else "n/a",
                     stats(e["gap_jpy"], 0, True), stats(e["gap_travel_hours"], 2, True), f"{e['cheapest_by_rate_not_best_same_nice_set']} of {e['n_same_nice_set']}", _reasons(e["ineligible_reasons"])])
    out += table(["VoT JPY/h", "Trips", "Eligible", "Lowest-rate hotel NOT best", "True-cost gap, JPY (lowest-rate hotel minus best)", "Travel-hours gap (lowest-rate hotel minus best; negative = it travels less)",
                  "Same, only where all hotels schedule the same nice-to-haves", "Ineligible (why)"], rows)
    f = h["flip"]
    if f:
        out += ["### Value-of-time flip point (range 0-3,000 JPY/h)", "",
                f"Analysed {f['n_analysed']} trips (feasible at all three hotels at the default value of time); the best hotel changes within the range in **{f['n_with_flip']}**. "
                + (f"First flip: {stats(f['first_flip_vot'], 0, True, ' JPY/h')}. {f['exact_crossing']} are exact crossings and {f['bisection_estimate']} are bisection estimates (approximate). " if f["n_with_flip"] else "")
                + f"Analyses the routine itself flags approximate: {f['analysis_flagged_approximate']} (it does so whenever a hotel's best plan changes between solved value-of-time points, because values in between are then bounded rather than solved, or when a solve was not proven optimal).", ""]
    else:
        out += ["Flip-point analysis was not run in this mode.", ""]
    return out


def _replan_section(m: dict) -> list[str]:
    r = m["replan"]
    if not r:
        return ["## F. Replanning", "", "Not run.", ""]
    def row(k, label):
        d = r[k]
        return [label, f"{d['applied']} of {d['n']}", stats_list(d["moved"], False), stats_list(d["cost_change_jpy"], False), d["infeasible"], d["rejected"]]
    out = ["## F. Replanning (disruption-aware vs naive full re-solve)", "",
           "Reuses `scripts/run_replan_evaluation.py` (`collect` and `summarise`), the same scenario logic as `docs/replan-results.md`. 'Moved' = an unchanged activity whose day changed "
           "or whose start shifted by more than 30 minutes.", ""]
    out += table(["Strategy", "Applied", "Unnecessarily moved per applied replan (lower is better)", "True-cost change, JPY (after - before)", "Infeasible", "Rejected before solving"],
                 [row("aware", "Disruption-aware"), row("naive", "Naive re-solve")])
    out += [f"Paired over {r['n_both_applied']} scenarios where both produced a plan: disruption-aware moved fewer activities in {r['aware_fewer_moves']}, the same number in {r['same_moves']}, "
            f"more in {r['aware_more_moves']}. Its final true cost minus the naive plan's: {stats_list(r['extra_cost_of_stability_jpy'], False)} JPY.", ""]
    return out


def stats_list(xs: list, favourable: bool) -> str:
    import statistics
    if not xs:
        return "n/a (N=0)"
    f = down if favourable else up
    return f"mean {f(statistics.fmean(xs), 2)}, median {f(statistics.median(xs), 1)}, min {min(xs)}, max {max(xs)} (N={len(xs)})"


def _runtime_section(m: dict, meta: dict) -> list[str]:
    s, rt = m["solver_status"], m["machine_dependent"]["solver_runtime_seconds"]
    def line(d):
        return ", ".join(f"{k} {v}" for k, v in sorted(d.items())) or "none"
    out = ["## H. Solver status and runtime", "",
           "Solver status is deterministic (fixed seed, one worker, deterministic-time limit; wall-clock limits lifted for this run). OPTIMAL = proven optimal; FEASIBLE = a plan was found but optimality was not proven in the limit; "
           "NOT_RUN = the request was rejected as infeasible before solving.", ""]
    out += table(["Stage", "Solver status counts"], [["Trip solves (A-D)", line(s["trip_solves"])], ["Hotel-comparison solves (E)", line(s["hotel_compare_solves"])], ["Replanning solves (F)", line(s["replan_solves"])]])
    out += ["**Wall-clock runtime (machine-dependent: depends on this computer and its load, not a property of the method).**", "",
            f"Solver time per generated trip: mean {up(rt['mean'], 3) if rt['mean'] is not None else 'n/a'} s, max {up(rt['max'], 3) if rt['max'] is not None else 'n/a'} s (N={rt['n']}). "
            f"Whole evaluation run ({meta['mode']} mode): {meta['elapsed_seconds']} s. The free hosting tier is slower (see docs/DEPLOY.md).", ""]
    return out


NOT_SHOWN = [
    "**Sample data.** 12 attractions, 3 hotels. Every record is sample or estimated; nothing is verified. Results may look different with other places.",
    "**Fictional hotels with tuned rates.** The hotel rates were tuned in Phase 4 for the demo, so the hotel result shows the model's behaviour on that dataset; it says nothing about real hotel markets.",
    "**Estimated travel times and fares.** Both are computed from straight-line distance (x1.3 detour, 20 km/h, +10 min per leg; fare 150 JPY + 20 JPY/km), not from a live routing service or real timetables.",
    "**A small, tuned demo.** Only 12 sights means few trips are really 'scattered'; the generator's constants (days, budgets, ordering) are judgement calls listed under Parameters.",
    "**Synthetic trips, not users.** No person used the planner; nothing here measures whether travellers find the plans good or how they trade off time and money.",
    "**Not live prices.** Admission prices, opening hours and room rates are not current and not checked against any source.",
    "**No significance testing.** There are no confidence intervals or tests; N is small and the trips are drawn from one seeded generator. Differences should not be extrapolated beyond this sample.",
    "**The language model is not measured here.** Explanation quality and natural-language parsing need a live model; see the opt-in `docs/llm-live-eval.md` (section G).",
    "**One machine.** Solver statuses depend on the OR-Tools version and platform; runtimes depend on the computer.",
]


def render_results(*, metrics: dict, scenarios, trips: list[dict], meta: dict, params: dict) -> str:
    n = metrics["n_trips"]
    out = ["# Evaluation results (SAMPLE data)", "",
           f"Generated {meta['date']} by `backend/scripts/run_evaluation.py` ({meta['mode']} mode). Code version: {meta['commit']}. Every number below was produced by that run; "
           "raw per-trip results are in `docs/eval-results.json`, the trips in `docs/eval-scenarios.json`. Claim-safe sentences generated from these numbers: `docs/README-claims.md`. "
           "Method: `docs/EVALUATION.md`.", ""]
    out += _scenario_section(scenarios) + _generated_section(metrics, params["seed"], n) + _travel_section(metrics) + _secondary_section(metrics) + _validation_section(metrics) + _budget_section(metrics)
    out += _must_section(metrics) + _hotel_section(metrics) + _replan_section(metrics)
    out += ["## G. Explanation and parsing", "",
            "Not measured here: they need a live model. They are covered by the opt-in script `backend/scripts/run_llm_live_eval.py`, which writes `docs/llm-live-eval.md` "
            + ("(that file exists in this repository)." if meta["live_eval_exists"] else "(that file does not exist: the live evaluation has NOT been run, so this report makes no claim about the model)."), ""]
    out += _runtime_section(metrics, meta)
    out += ["## Every generated trip", "", "Travel = total minutes incl. hotel legs. 'placed' = attractions scheduled. Verdicts: P = pass, W = pass with warnings, F = fail, - = no plan.", ""]
    short = {"pass": "P", "pass_with_warnings": "W", "fail": "F", "no_plan": "-"}
    rows = []
    for t in trips:
        def cell(k):
            r = t[k]
            return f"{r['status'][:4]} {r['travel_minutes'] if r['travel_minutes'] is not None else '-'} min, {len(r['placed'])} placed, {short[r['validator']]}"
        rows.append([t["id"], t["hotel_id"][6:], t["days"], t["n_requested"], t["n_must"], t["budget_kind"], cell("solver") + f" ({t['solver']['solver_status']})", cell("naive"), cell("nn")])
    out += table(["Trip", "Hotel", "Days", "Requested", "Must", "Budget", "Solver", "Input-order", "Nearest-neighbour"], rows)
    out += ["## Parameters and seeds", ""]
    out += table(["Parameter", "Value"], [[k, v] for k, v in params["rows"]])
    out += ["## WHAT THESE NUMBERS DO NOT SHOW", ""] + [f"- {x}" for x in NOT_SHOWN] + [""]
    return "\n".join(out)


def render_claims(claims: list[tuple[str, str]], meta: dict, params: dict) -> str:
    out = ["# Claim-safe sentences (generated)", "",
           f"Generated {meta['date']} by `backend/scripts/run_evaluation.py` ({meta['mode']} mode, seed {params['seed']}, {params['n_trips']} trips). Code version: {meta['commit']}. "
           "Each sentence is produced from the measured numbers in `docs/eval-results.json`; paste whole sentences, keeping the N and the caveat. "
           "If you re-run the evaluation, regenerate this file and re-paste: do not edit numbers by hand. No sentence claims statistical significance.", ""]
    out += [f"- **{cid}**: {text}" for cid, text in claims] + [""]
    return "\n".join(out)
