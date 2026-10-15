# Lighthouse results (measured)

Generated 2026-10-15T10:01:21.205Z by `frontend/scripts/run-lighthouse.mjs` with lighthouse 13.5.0, mobile (default), simulated throttling. Production build, real backend in sample mode, local machine. Scores vary run to run and with the machine; they are what Lighthouse reported, unadjusted.

| Page | Mode | Performance | Accessibility | Best practices |
|---|---|---|---|---|
| Home (create trip) | navigation | 97 | 100 | 100 |
| Proof | navigation | 93 | 100 | 100 |
| Itinerary (after the example flow) | snapshot | not measured | 100 | 100 |

The itinerary page is measured as a snapshot of the real page after the example flow (its data lives in memory only, so a fresh navigation would show the empty state). Lighthouse does not measure performance for a snapshot, so that cell is "not measured".

**Home (create trip) metrics:** First Contentful Paint 2.0 s, Largest Contentful Paint 2.2 s, Total Blocking Time 0 ms, Cumulative Layout Shift 0.03

**Home (create trip):** no failed accessibility or best-practices audits.

**Proof metrics:** First Contentful Paint 2.0 s, Largest Contentful Paint 2.9 s, Total Blocking Time 0 ms, Cumulative Layout Shift 0

**Proof:** no failed accessibility or best-practices audits.

**Itinerary (after the example flow):** no failed accessibility or best-practices audits.
