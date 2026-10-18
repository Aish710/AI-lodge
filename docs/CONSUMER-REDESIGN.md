# Consumer interface redesign

## Audit before implementation — 2026-10-18

Source reviewed: Plan.vue, Trip.vue and their existing components. The supplied attachment contains a written brief, but no screenshots. No production URL was supplied initially. Screenshot-specific and deployment-specific diagnoses therefore remain unverified.

1. Trip renders hotel selection, recommendation methodology and explanation before the daily itinerary. The primary result is buried.
2. A single Trip column includes two AI workflows, repair, what-if, manual editing, the explorer, cost tables, hotel breakdown and evidence. Finding a tool requires unrelated scrolling.
3. All days are initially selected. A long timeline outgrows the adjacent map, leaving blank space and making day navigation difficult.
4. The drag editor is labelled as a comparison tool, rather than being discoverable beside the itinerary. It lacks a draft undo/reset control.
5. Plan begins with AI, destination, sample entry and worked examples before essentials; style inference and advanced input compete with essential choices.
6. Attraction categories exist, but text search does not. Interest highlighting adds another row of controls that resembles filtering.
7. Modelled cash including rooms is present in the latest Trip source, but its fallback substitutes sights/transport when a cost summary is absent. That can mislabel a subtotal as a room-inclusive total.
8. Several rendering paths still say “true cost” or “full true-cost breakdown”. Hotel “Best overall” labels need a bounded comparison scope.
9. Dense badges, duplicated explanation and small text make the hierarchy hard to scan. On mobile, multi-column tables need horizontal scrolling and the navigation needs larger targets.
10. Feasibility failures, unknown prices, budget scope and provisional hours must remain visible through progressive disclosure. Hiding them with diagnostics would be unsafe.

## Intended information architecture

Plan: destination → essentials → searchable attractions, with optional AI/style/advanced controls disclosed on request and a persistent planning summary/action.

Your Trip: shared destination, duration, hotel, cash/coverage/travel/feasibility overview and critical notices. Sections: Itinerary; Hotels & Costs; AI Planner; Compare & What-if; Details & Evidence. Daily map/timeline and draft editing belong together. AI handoffs must activate their destination before moving focus. Tabs must preserve drafts and preview state.

## Boundaries

Frontend-only redesign. Existing API operations, solver, validator, fingerprints, confirmation dialogs and explicit Apply boundaries are retained. Budget still covers sights and transport only. No paid model calls, push, deployment or publication. Local commit requested.
