# Solver design

Facts here describe the code in `backend/app/optimiser/solver.py`. All data is sample or estimated.

## Principle
The LLM never builds the schedule. A deterministic CP-SAT model chooses the plan, and an independent validator re-checks it. The solver reports infeasibility with specific, computed reasons instead of forcing a plan.

## Inputs
`Preferences`, a hotel id and the dataset (attractions, hours, estimated travel-time and fare matrix).

## Variables (per trip day)
- One optional node per (attraction, usable opening range) that can be visited that day. Closed days and ranges too short for the visit create no node. Unknown-hours attractions get a node only if `allow_unknown_hours` is true (flagged later).
- `present` (bool) and `start` (integer minute inside the opening range) per node.
- Arc literals for hotel to node, node to node and node to hotel, chosen through `AddCircuit` (the hotel is the depot; absent nodes take a self-loop).

## Hard constraints
1. Circuit: each day is one route that starts and ends at the hotel.
2. Travel: arc i to j implies `start_j >= start_i + duration_i + travel(i, j)`. The first leg from the hotel respects `day_start`; the last leg back must finish by `day_end`. Consecutive stops therefore cannot overlap.
3. Opening hours for that weekday (`start_weekday + day`); closed is excluded; visit must finish before closing.
4. Every must-visit (and every locked item) exactly once; other attractions at most once. If a must-visit cannot be placed the status is infeasible; it is never dropped.
5. Locked items: single node on the locked day with fixed start.
6. At most `PACE_MAX_PER_DAY[pace]` attractions per day (relaxed 2, balanced 3, packed 4).
7. Strict budget: admissions + estimated fares (hotel legs included) <= budget.
8. Skipped attractions are never candidates (unless locked, which is reported as a conflict).

## Objective (minimise, integers)
Each term is normalised to roughly 0..1, multiplied by its weight (in `config.py`), then scaled by `OBJECTIVE_SCALE` = 100,000 and rounded to integer coefficients:

| Term | Normalisation | Weight |
|---|---|---|
| Travel | total travel minutes / (days x day-window minutes) | `W_TRAVEL` = 3 |
| Cost | (admissions + fares JPY) / (5,000 x days) | `W_COST` = 2 |
| Missed nice-to-have | missed count / number of nice-to-have candidates | `W_MISSED` = 5 |
| Pace fit | (busiest day - quietest day) / pace cap | `W_PACE` = 1 |
| Over soft budget | overshoot JPY / cost reference | `W_OVER_BUDGET` = 4 |
| Disruption | reserved for Phase 4 | `W_DISRUPTION` = 3 (unused) |

Missed attractions carry the largest weight so a plan fills the pace cap when it can; travel and cost then decide which attractions and in what order. The weights are judgement calls, not tuned on data.

## Determinism
Fixed seed 42, one worker, wall limit 20 s and deterministic-time limit 5. Same input gives the same schedule (tested). Result includes solver status (`OPTIMAL` or `FEASIBLE` if the limit was reached) and runtime.

## Infeasibility handling
A pre-check computes conflicts from data before solving: unknown ids, closed on all trip days, unknown hours not allowed, attraction cannot fit one day with its round trip from the hotel, total required time lower bound, pace cap, strict-budget lower bound, impossible or overlapping locks. If the solver itself proves infeasibility, a generic "jointly impossible" conflict is returned. Alternatives (add a day, relax a strict budget, allow unknown hours, extend the day end by 2 h, demote one must-visit) are included only if re-solving that relaxed problem actually succeeded.

## Validator
Separate package; imports only schemas and the data loader, recomputes times, travel and costs from the dataset, and ignores costs reported by the schedule. A schedule with any failing check is reported as `fail`. Warnings (unknown hours used, unknown prices excluded, estimated transport, advance booking) give `pass_with_warnings`.

## Limitations
- Travel times and fares are straight-line estimates, not real transit data.
- `max_walking_minutes_per_day` and `interests` are not used.
- Public holidays and seasonal hours are not modelled.
- Visits are one per attraction, with fixed durations.
- For 5-7 day trips with every attraction open as a candidate the solver stops at its limit with a good but not proven-optimal plan (about 6 s here).
- Alternatives are a short fixed list of relaxations, not a full search.

## Hotel comparison (Phase 3)

**True cost (JPY, integers):**
`true_cost = rooms + admissions + transport + time_cost + missed_penalty`
- `rooms = nightly_rate x nights` (nights default `days - 1`, overridable)
- `admissions` = known prices only; unknown prices are excluded and listed
- `transport` = estimated fares including hotel legs
- `time_cost = round(travel_minutes x value_of_time_per_hour / 60)`
- `missed_penalty = 3 hours x the selected city's default value of time x visitable nice-to-have attractions not scheduled` (judgement call, `money.py`): Tokyo 3,000 JPY, Seoul 45,000 KRW, Singapore 54 SGD, Kuala Lumpur 135 MYR.

This was tuned after seeing multi-city results, so it is a modelling choice, not an experimental finding. A fixed `3,000` in each city currency was roughly acceptable in Tokyo but far too small in Seoul, where it made the optimiser skip nearly every optional sight.

**Objective for the comparison path** (`ObjectiveSpec("true_cost")`): minimise admissions + fares + time cost + penalty for that hotel, so each hotel gets the plan that is cheapest for it. Rooms are constant per hotel and do not affect the itinerary; they only enter the ranking. The default Phase 2 objective is unchanged.

**Unit handling.** CP-SAT needs integers. VoT is JPY per hour, travel is in minutes, so time cost is `VoT x minutes / 60`. The model multiplies the whole objective by 60: `60*(admissions + fares) + VoT x minutes + 60*penalty*missed`. Every coefficient is an integer and `objective / 60` equals the JPY figure exactly (a test checks this). Displayed time cost is rounded to the nearest JPY, and `true_cost` is the sum of the displayed lines.

**Cache and sensitivity rule.** For a plan with non-time cost K and T travel minutes, cost(v) = K + T x v / 60 is linear in VoT v. If the same (K, T) is optimal at v = a and v = b, it is optimal for all v in [a, b], so those hotels need no more solves there. The sensitivity run solves the range ends for each hotel, halves an interval only when some hotel's (K, T) differs between its ends (max depth 3, max 36 solves), and computes grid values and winners analytically. A winner change inside a segment with equal ends is an exact line crossing, `v* = 60 (K_q - K_p) / (T_p - T_q)`. Where plans still differ at the depth limit, values are upper bounds (the cheaper of the two known plans), flips come from bisection, and the result is flagged approximate. Solves are cached per call by (hotel, hash of itinerary-affecting preferences, VoT, penalty); there is no cache across requests.

**Time limit.** The whole comparison (hotels plus sensitivity) has a 10 s default budget. Remaining time is split across the hotels still to solve. If it runs out, remaining hotels are `skipped` and the result is labelled partial and approximate.

**Limitations.** Unknown prices count as 0 inside the optimiser (shown as warnings, but this favours those attractions). The penalty is a judgement. Sensitivity assumes at most one winner change per interval between evaluation points.

## Replanning (Phase 4)

**Operations.** `lock`, `unlock`, `remove`, `move` (a lock at the new slot), `change_budget`, `switch_hotel`, applied together in one solve to new `Preferences` (locks go into `locked`, removals into `skip`, a confirmed must-visit removal also leaves `must_visit`). Operations that contradict each other or the constraints (lock+remove, lock outside opening hours, overlapping locks, unknown ids) are rejected before solving. The service is stateless: nothing is stored.

**Objective.** The Phase 3 true cost for the hotel (fixed unless `switch_hotel`) plus a disruption term, all as integers in 1/60 JPY: `60*(admissions + fares) + VoT*travel_min + 60*penalty*missed + 60*W_DISRUPTION*moved + drift`.

**"Moved".** An activity in both plans that the user did not lock or move counts as moved if its day changes or its start shifts by MORE than `MOVE_THRESHOLD_MINUTES` (30). In the model, a Boolean `ok` says "same day and within the threshold of the old start"; `moved >= present AND NOT ok`. Locked/moved-by-user items are excluded from the penalty. Measured on the result with the same definition by `replan._build_diff`, independent of the model.

**Units.** `W_DISRUPTION` is JPY-equivalent per moved activity (1,500 by default, a judgement call, shown in every diff). It is multiplied by 60 like every other JPY term. `drift` is 1 unit (1/60 JPY) per minute of start shift on the same day: negligible against real trade-offs, but it makes the old plan the unique best among otherwise equal plans, so a no-op replan returns the identical schedule.

**Warm start.** The previous plan is passed to CP-SAT as hints (presence and start times of nodes matching the old day and slot). It speeds the solve; correctness does not depend on it. Per-replan limit: `REPLAN_TIME_LIMIT_SECONDS` (5 s). A result that is not OPTIMAL is labelled approximate.

**Unknown prices.** Optimiser-only placeholder = median of known admission prices. It appears in the objective, never in constraints, totals, or the validator. The diff reports the placeholder separately.

**Failure behaviour.** Infeasible replans return the specific pre-check or solver conflicts and the ORIGINAL plan unchanged. A new plan that the independent validator rejects is not applied (`rejected_by_validator`).

**Not modelled.** Public holidays, `max_walking_minutes_per_day` and `interests` remain unmodelled.


## Balance nudge (added for the live app, 2026-10-18)

The live routes (`/optimise`, `/compare-hotels` and its sensitivity runs, `/replan`) add two small terms to the true-cost objective so that a trip does not leave whole days empty while sights remain and the stops are spread rather than piled onto a few days:

- an empty trip day is charged 2.5 hours of the city's default value of time (Tokyo: 2,500 JPY), `money.empty_day_penalty`;
- each stop of difference between the busiest and the quietest day is charged 0.5 hour (Tokyo: 500 JPY), `money.spread_penalty`.

They are tie-breakers inside the optimiser only. They are never added to a displayed cost, a true-cost figure, the budget or the validator; every hard rule (opening hours, pace cap, daily limits, strict budget, locks, must-visits) is unchanged, and an empty day is still produced when nothing can fill it. The committed evaluation, baseline and hotel-comparison files were produced WITHOUT the nudge and are unchanged: they describe the same objective minus these two terms (`tests/test_evaluation.py::test_headline_solver_runs_the_same_objective_as_post_optimise` runs the route with the nudge off and requires an exact match). `docs/worked-example.md` is regenerated from the live app and therefore includes the nudge.
