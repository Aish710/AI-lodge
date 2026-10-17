<script setup>
import { computed } from 'vue'
import { PITCH, PROJECT_NAME, REPO_URL } from '../brand.js'
import { store } from '../store.js'
const relay = computed(() => (store.health?.llm_relay ? store.health.llm_endpoint : null))
const cityNames = computed(() => (store.cities.length ? store.cities.map((c) => c.display_name).join(', ') : 'several sample cities'))
</script>
<template>
  <div class="stack">
    <div><h1>How {{ PROJECT_NAME }} works</h1>
      <p class="lead fw-semibold mb-1" data-testid="pitch">{{ PITCH }}</p>
      <p class="muted mb-0">{{ PROJECT_NAME }} plans a trip to one city at a time ({{ cityNames }}) by choosing the hotel and the itinerary together, then showing its working.</p></div>

    <section class="card-soft" aria-labelledby="what-h">
      <h2 id="what-h" class="h5">What it is</h2>
      <p class="mb-2">Hotels that look cheap can cost more once travel time and fares are counted. The app plans the days around each hotel, then compares hotels by <strong>true cost</strong>: rooms + admissions + estimated transport + travel time valued at what an hour of your time is worth + a charge for each optional sight left out. Every line of that calculation is shown.</p>
      <p class="mb-0">It is a hackathon project built on <strong>sample data</strong>: 10 to 12 sights and 3 made-up demo hotels per city, with prices, hours and travel times that are samples or estimates. It gives no live quotes and makes no bookings.</p>
    </section>

    <section class="card-soft" aria-labelledby="arch-h" data-testid="architecture">
      <h2 id="arch-h" class="h5">How it works</h2>
      <figure class="mb-2">
        <svg viewBox="0 0 760 250" role="img" aria-labelledby="arch-t arch-d" class="w-100" style="max-width:760px" font-family="Inter Variable, system-ui, sans-serif" font-size="13">
          <title id="arch-t">Architecture: your request is cleaned, optionally read by the AI, planned by the optimiser, re-checked by the validator, and optionally explained</title>
          <desc id="arch-d">Six boxes in a row: Your request, Clean-up, AI assistant (optional, proposes only), Optimiser (decides), Validator (re-checks), Result with explanation. A dashed line shows that sample mode skips the AI box.</desc>
          <defs><marker id="ah" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8z" fill="#1b2733"/></marker></defs>
          <g stroke="#1b2733" stroke-width="1.5" fill="#fff">
            <rect x="8" y="70" width="104" height="70" rx="10"/><rect x="132" y="70" width="104" height="70" rx="10"/>
            <rect x="256" y="70" width="124" height="70" rx="10" fill="#e9eef5"/><rect x="400" y="70" width="112" height="70" rx="10" fill="#e3f0ee"/>
            <rect x="532" y="70" width="104" height="70" rx="10" fill="#e3f0ee"/><rect x="656" y="70" width="96" height="70" rx="10"/>
          </g>
          <g fill="#1b2733" text-anchor="middle">
            <text x="60" y="100" font-weight="700">Your</text><text x="60" y="118">request</text>
            <text x="184" y="100" font-weight="700">Clean-up</text><text x="184" y="118" font-size="11">length cap, data</text><text x="184" y="132" font-size="11">tags</text>
            <text x="318" y="96" font-weight="700">AI assistant</text><text x="318" y="112" font-size="11">optional; reads words,</text><text x="318" y="126" font-size="11">only PROPOSES</text>
            <text x="456" y="96" font-weight="700">Optimiser</text><text x="456" y="112" font-size="11">OR-Tools CP-SAT</text><text x="456" y="126" font-size="11">DECIDES the plan</text>
            <text x="584" y="96" font-weight="700">Validator</text><text x="584" y="112" font-size="11">written separately,</text><text x="584" y="126" font-size="11">re-checks every rule</text>
            <text x="704" y="96" font-weight="700">Result</text><text x="704" y="112" font-size="11">+ explanation</text><text x="704" y="126" font-size="11">(numbers checked)</text>
          </g>
          <g stroke="#1b2733" stroke-width="1.5" marker-end="url(#ah)"><line x1="112" y1="105" x2="130" y2="105"/><line x1="236" y1="105" x2="254" y2="105"/><line x1="380" y1="105" x2="398" y2="105"/><line x1="512" y1="105" x2="530" y2="105"/><line x1="636" y1="105" x2="654" y2="105"/></g>
          <path d="M184 150 V196 H456 V142" fill="none" stroke="#7a4e00" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#ah)"/>
          <text x="320" y="214" text-anchor="middle" fill="#7a4e00" font-size="12">Sample mode: the form goes straight to the optimiser. Everything except the AI still works.</text>
        </svg>
        <figcaption class="small muted">Boxes in blue and green are the parts that matter most: the AI never decides the schedule; the optimiser does, and the validator checks it.</figcaption>
      </figure>
      <ol class="mb-0">
        <li>Your text or form is cleaned. Text is wrapped as data, never mixed into the AI's instructions. One trip covers one city: every request carries it, and a place or hotel from another city is refused.</li>
        <li>The AI assistant (only if configured and available) turns words into a draft you can edit, or into a proposed change you can accept or discard. Names are matched against the selected city's data; a place that is not in it cannot be scheduled. A request about another city is caught by code (not by the AI) and only offers a switch.</li>
        <li>The optimiser (a constraint solver) builds the best feasible itinerary for each hotel and reports a specific conflict if the request is impossible.</li>
        <li>An independently written validator re-checks every hard rule on the result and reports pass, warning or fail.</li>
        <li>If you ask, the AI writes a short explanation of the computed result. Every number in it is checked against the computed facts; if anything does not match, a template summary is shown instead.</li>
      </ol>
    </section>

    <section class="card-soft" aria-labelledby="ai-h">
      <h2 id="ai-h" class="h5">Exactly how the AI is used</h2>
      <ul class="mb-0">
        <li><strong>It parses language:</strong> free text into a draft of the trip form, or into proposed edits. Proposals fill an editable form or a queue; nothing runs until you confirm.</li>
        <li><strong>It explains computed results,</strong> only when you click "Explain this result". It is told the computed numbers and names; it cannot change them.</li>
        <li><strong>It never decides the schedule</strong> and never supplies prices, opening hours or travel times. Those come from the dataset and the optimiser.</li>
        <li><strong>It never confirms removing a must-visit.</strong> That needs your explicit click.</li>
        <li><strong>The app works without it.</strong> In sample mode (no key, an outage, or the daily limit reached) the form, comparison, itinerary, replanning and template explanations all work.</li>
        <li>Place descriptions are never sent to the AI and are not shown in this interface.</li>
      </ul>
    </section>

    <section class="card-soft" aria-labelledby="lim-h">
      <h2 id="lim-h" class="h5">Limitations</h2>
      <ul class="mb-0">
        <li>Sample data only: made-up demo hotels, estimated prices, hours and travel times (straight-line distance, not real transit). Unknown prices and hours are shown as "unknown" and never assumed. No bookings, no live availability, no walking-distance limit yet.</li>
        <li>Measured results come from seeded synthetic trips, not from users. See the <router-link to="/proof">Proof page</router-link> for what was measured and what it does not show.</li>
        <li>Detecting an unsupported city depends on the AI reporting it; with no AI, names that aren't in the selected city's data are reported as not found.</li>
        <li>How well the AI reads real requests has not been measured yet: that evaluation is opt-in and has not been run.</li>
        <li data-testid="interests-limit"><strong>Interests only highlight.</strong> Choosing "Most interested in" (or the AI reading interests from your text) marks matching sights and lists them first. It does not change the plan. The planner uses your Must visit / Include if it fits / Skip choices only.</li>
        <li data-testid="cash-vs-true"><strong>Cash cost is not true cost.</strong> Cash cost is money spent (admissions, estimated transport, rooms). True cost adds the value you put on your travel time and a charge for optional sights left out; it exists only to compare hotels and is never money.</li>
        <li>Themes (Sightseeing, Shopping, Food &amp; drink) are a grouping in the interface, one primary theme per sight; the planner never sees them. Some themes are thin in the sample data and say so.</li>
        <li>On a free host the server sleeps when idle, so the first request can take about a minute.</li>
      </ul>
    </section>

    <section id="privacy" class="card-soft" aria-labelledby="priv-h" data-testid="privacy">
      <h2 id="priv-h" class="h5">Privacy</h2>
      <ul class="mb-0">
        <li><strong>No accounts, and nothing is stored.</strong> There is no database. Plans are computed per request; the replanning API is stateless. This page keeps what you type in memory only (no cookies, no local storage) and "Reset" clears it.</li>
        <li><strong>What is sent:</strong> your trip details and the changes you make, to compute plans. Free text you type into the AI boxes is cleaned and sent to the AI provider only when the assistant is on; for replanning, the names of the sights in your current plan go with it. Explanations send computed facts about the result. <strong>Place descriptions are never sent.</strong> The provider handles requests under its own terms.</li>
        <li v-if="relay" data-testid="relay-note"><strong>Third-party gateway in use:</strong> this deployment reaches the AI model through a third-party gateway ({{ relay }}). Whatever the assistant is sent (your cleaned text, the sight names in your plan, computed facts) passes through that gateway to the model provider, so it is not a direct connection to the provider. The gateway's own terms and retention apply too, and this project does not control them. The key never reaches your browser.</li>
        <li v-else-if="store.health?.llm_configured" data-testid="direct-note"><strong>AI connection:</strong> this deployment connects to the model provider directly (no gateway).</li>
        <li><strong>What is logged on the server:</strong> metadata only (request id, route, status, timing, counts). Never your text, prompts, model output, keys or your IP address.</li>
        <li><strong>Third parties:</strong> the map loads tiles from OpenStreetMap, which sees your IP address and the area you view. There are no analytics, trackers or other third-party scripts.</li>
      </ul>
    </section>

    <p class="mb-0">Source code: <a :href="REPO_URL" target="_blank" rel="noopener noreferrer">{{ REPO_URL }}</a></p>
  </div>
</template>
