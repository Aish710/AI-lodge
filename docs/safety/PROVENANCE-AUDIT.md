# Provenance audit: what the data says it knows

Audited from the code and data on 2026-10-18; no model-facing contract was changed.

| Kind of value | Where it comes from | How it is labelled today | Gap |
|---|---|---|---|
| Hotel names and nightly rates | Made-up sample data (`cities/*/hotels.json`) | "Demo hotel", "sample prices" in the UI; `source_status: sample` on records; never verified | None known |
| Attraction coordinates, prices, hours | Sample data; `source_status` per record; Singapore has per-field verification records | `sample` / verification counts on the Proof page; unknown prices carry `cost_status: unknown`; unknown hours carry the `opening_hours_unknown` flag | Hours and prices are labelled per stop, not per field in the API response |
| Travel minutes and fares | Estimated from straight-line distances (`matrix_meta: estimated`) | "estimated" badges next to travel times and transport | The word is in UI strings, not a structured field on each stop |
| Unknown admission | `null` in data; objective-only placeholder | Listed as unknown, never counted as zero; placeholder never in reported totals | Fine |
| Score / generalised cost | Computed | Labelled "not what you pay" in the Explorer, comparisons and Proof | Older panels use "true cost" |
| Verified vs conditional plans | Validator | `verification: verified | conditional | none` in the feasibility report (new), "Opening hours unverified" on stops | Prices are not part of `verification` (unknown prices are a separate warning) |

Not done, on purpose: adding per-field provenance to every API object would change the facts passed to the explanation model and therefore the AI code's evidence. Recommended next step if you accept re-running the live evidence: add `provenance` (`verified | sample | estimated | unknown`) beside each fact the explanation sees, and have the citation checker require it.
