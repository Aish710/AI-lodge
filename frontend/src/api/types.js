/**
 * JSDoc mirrors of the backend schemas (backend/app/schemas.py, optimiser/*, validator/*). Hand-maintained on purpose: the backend
 * keeps its OpenAPI schema off by default (ENABLE_DOCS=0), and a build step that needs a running server would make the build fragile.
 * Nothing in the UI invents fields that are not listed here.
 *
 * @typedef {'mon'|'tue'|'wed'|'thu'|'fri'|'sat'|'sun'} Weekday
 * @typedef {'sample'|'estimated'|'verified'} SourceStatus
 *
 * @typedef {Object} Place   one entry of GET /data/places `attractions` (no description: it is untrusted and never sent)
 * @property {string} id @property {string} name @property {string} area @property {number} lat @property {number} lon
 * @property {string} category @property {string} priority @property {number} duration_minutes
 * @property {number|null} admission_cost JPY, null = unknown
 * @property {boolean} indoor @property {boolean} advance_booking_required
 * @property {Record<Weekday, Array<[string,string]>|null|'unknown'>} opening_hours null = closed, 'unknown' = not known
 * @property {{record: SourceStatus, hours: SourceStatus, cost: SourceStatus}} source
 *
 * @typedef {Object} HotelPlace
 * @property {string} id @property {string} name @property {string} area @property {number} lat @property {number} lon
 * @property {number} nightly_rate @property {{record: SourceStatus}} source
 *
 * @typedef {Object} Preferences   request body for /optimise, /compare-hotels, /replan (strict: unknown fields are rejected)
 * @property {number} days @property {number|null} budget @property {boolean} strict_budget @property {'relaxed'|'balanced'|'packed'} pace
 * @property {string[]} interests @property {string[]} must_visit @property {string[]} skip @property {string} day_start @property {string} day_end
 * @property {number} value_of_time_per_hour @property {number} max_walking_minutes_per_day @property {number} start_weekday 0=Mon..6=Sun
 * @property {boolean} allow_unknown_hours @property {number|null} nights @property {Array<{attraction_id:string,day:number,start_time:string}>} locked
 *
 * @typedef {Object} Stop
 * @property {string} attraction_id @property {string} start @property {string} end @property {number} travel_minutes_from_previous
 * @property {number} transport_jpy_from_previous @property {number} cost @property {'known'|'unknown'} cost_status
 * @property {boolean} is_must_visit @property {string[]} uncertainty_flags
 *
 * @typedef {Object} DayPlan
 * @property {number} day @property {Weekday} weekday @property {Stop[]} stops @property {string|null} hotel_departure @property {string|null} hotel_return
 * @property {number} return_travel_minutes @property {number} return_transport_jpy
 *
 * @typedef {Object} Conflict @property {string} code @property {string} message @property {string[]} attraction_ids
 * @typedef {Object} Alternative @property {string} kind @property {string} message @property {Object} details
 *
 * @typedef {Object} SolveResult
 * @property {'feasible'|'infeasible'} status @property {string} hotel_id @property {DayPlan[]} days
 * @property {{travel_minutes:number,admissions_jpy:number,transport_jpy:number,total_jpy:number,unknown_cost_items:string[],attractions_scheduled:number}} totals
 * @property {Conflict[]} conflicts @property {Alternative[]} alternatives @property {string[]} notes @property {string[]} missed_preferences
 * @property {{solver:string,solver_status:string,runtime_seconds:number,seed:number,objective:number|null}} solver_meta
 *
 * @typedef {Object} Check @property {string} id @property {string} name @property {'pass'|'warning'|'fail'} status @property {string} message @property {string[]} stop_ids
 * @typedef {Object} FeasibilityReport @property {'pass'|'pass_with_warnings'|'fail'} overall @property {Check[]} checks
 * @property {string[]} data_quality_warnings @property {string} summary
 *
 * @typedef {Object} Explanation @property {string} text @property {'llm'|'template'} source @property {string[]} warnings @property {string|null} reason
 *
 * @typedef {Object} OptimiseResponse   POST /optimise
 * @property {SolveResult} result @property {FeasibilityReport} feasibility_report @property {boolean} approximate
 * @property {number} nights_used @property {string} nights_source @property {Explanation} [explanation] @property {string} [approximate_note]
 *
 * @typedef {Object} ErrorBody   every non-2xx response: {error:{code,message,details,request_id}}
 */
export {}
