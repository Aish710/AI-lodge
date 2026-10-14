# Demo script (about 90 seconds)

Shows one success and one correctly handled failure. Each step names the judging criterion it serves: **AI** (AI Integration Effectiveness), **Safety** (LLM Safety and Responsible AI), **Value** (Usefulness and Business Value). Say the words in your own voice; the points matter more than the wording. Everything on screen comes from the app; do not quote numbers you have not seen on screen.

**Before you start (30 s of prep, not part of the 90):** open the live site in a fresh window, wait until the "Waking the server" notice has gone and the mode indicator is shown. Have `/evidence` ready in a second tab.

| Time | Click | Say | Criterion |
|---|---|---|---|
| 0:00 | Stay on the first page. Point at the yellow banner and the mode indicator. | "Planning a trip means picking a hotel and a plan together. This uses sample data only, and the banner says so. The AI is optional: the indicator shows whether it is on." | Safety |
| 0:10 | Click **Load example trip**. | "The example deliberately uses a high value of time, as its label says, to show the trade-off. It is not typical; the evidence page shows how often it matters." | Safety, Value |
| 0:18 | The hotel table appears. Point at the true-cost rows and the callout. | "Every line of the true cost is shown: rooms, admissions, transport, travel time at my value of time, and what I give up by skipping sights. The callout appears only because the planner says the cheapest rate is not the best value here." | Value |
| 0:32 | Click **Use this hotel** on the highlighted column. | "Now the itinerary for that hotel." | Value |
| 0:36 | Point at the map, then the feasibility report. | "An independent validator re-checked every rule. Warnings stay visible. The 'Not scheduled' box lists sights it left out on purpose and why." | Safety |
| 0:48 | Click **Lock** on the first stop, then **Remove** on a sight without the Must visit tag. Click **Apply changes**. | "Edits queue up and go to the planner in one call. I never edit the schedule in the browser." | AI (planner decides), Safety |
| 1:00 | Point at the diff warnings and the true-cost row. | "The change looks like a saving, but the planner flags that the set of sights changed, so it is not a pure saving. That warning sits next to the number." | Safety |
| 1:10 | Click **Restore previous plan**. | "I can go back to the earlier plan." | Value |
| 1:14 | Go to the first page, click **Try an impossible trip**. | "Now a request that cannot work: a must-visit with unknown opening hours." | Safety |
| 1:20 | Point at the conflict panel; click the offered alternative. | "This is a result, not an error: it names the conflict and offers options that were actually solved. One click makes it feasible, and the unknown hours are flagged, never assumed open." | Safety, Value |
| 1:30 | Open the **Evidence** tab and scroll to "Read this first". | "Measured on seeded sample trips, including the weak results, with what the numbers do not show. The AI scenarios use a stand-in; a live AI evaluation is a separate, opt-in step." | Safety |

**AI Integration talking point (use it where it fits, or in the Q and A):** the language model only reads requests and explains computed results; the optimiser decides the plan and the validator re-checks it. The explanation is opt-in per click and every number in it is checked against the computed facts; without the AI, template summaries are shown instead.

## If something is not as expected
- **The server is cold** (first request slow): the page says "Waking the server, this can take about a minute". Do not click anything; talk through the architecture on the About page until it disappears. Better: open the site one minute before you start.
- **The comparison's value-of-time analysis is slow** on the free host: the table is already usable. Say "the slower part is still computing, and I can cancel it", or press Cancel.
- **The AI is unavailable or the daily limit is reached** (or no key is set): the app shows "Sample mode (AI unavailable)". Say so and skip the "Explain" and natural-language boxes; the calm message in those boxes is itself part of the story: "everything else still works."
- **A 429 countdown appears:** wait for it to finish; the buttons re-enable on their own. Do not refresh.
- **Map tiles do not load:** the numbered list next to the map has the same information; carry on.
- **An error panel appears** (a real failure, in red with a request id): read the message, press "Try again" once, and move on to the Evidence tab.
