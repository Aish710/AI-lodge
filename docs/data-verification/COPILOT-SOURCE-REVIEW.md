# Demonstration-city source review

Reviewed 2026-10-18, web-assisted; not human verification. Singapore remains the demonstration city because it already has field-level official-source checks. Tokyo, Seoul and Kuala Lumpur remain unchecked sample packs. No source status has been silently promoted and no price has been invented during this upgrade.

The new places API and card disclosures expose the original field states, source URL, check date, scope notes and unresolved booking/admission questions. A sample record can contain a source-checked field without becoming a verified itinerary or live quote.

The [Singapore Botanic Gardens visitor page](https://sbg.nparks.gov.sg/visit/general-info/) supports daily garden access and distinguishes the paid National Orchid Garden. The app's existing midnight representation stops at 23:59; the separate paid area is not modelled. This review did not overwrite the original recorded check date.

The [Gardens by the Bay opening-hours page](https://www.gardensbythebay.com.sg/en/plan-your-visit/opening-hours.html) distinguishes the outdoor gardens from conservatories. The existing Gardens record has a scope mismatch: its notes interpret the hours as Flower Dome while its name/aliases can imply outdoor areas. The admission field is explicitly unchecked and not a verified non-resident quote. The new disclosure exposes this limitation; splitting this record into properly priced, scoped sub-attractions needs a separately verified data update and regeneration of matrices/fixtures. It is not fixed by relabelling the whole record verified.

[OneMap routing documentation](https://www.onemap.gov.sg/apidocs/routing) supports Singapore walking, driving, cycling and public-transport queries and requires an API access token. It documents quota/error responses. A deployable integration needs an account, token handling, a routing-mode decision, quota/caching and licensing review, and explicit routing provenance. No token was requested or provisioned, no route was fetched, and current matrices remain labelled estimates. A Singapore-specific integration would not establish coverage for the other cities. Availability of an API is not proof of a cost-free, licence-cleared production integration.

Hotels in all four packs remain fictional with illustrative rates. No real property identity, current price or publicly verified hotel location is claimed. Official attraction checks do not validate a hotel, estimated duration, travel matrix or foreign-exchange rate.
