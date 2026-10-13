<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import LoadingBlock from '../components/LoadingBlock.vue'
import ErrorPanel from '../components/ErrorPanel.vue'
import SourceBadge from '../components/SourceBadge.vue'
import { store, runCompare, ensureComparison, chooseHotel, rateLimited, currentPrefs } from '../store.js'
import { hotelCallout } from '../lib/rules.js'
import { formatJpy, formatSgd, minutesToHm, UNKNOWN } from '../lib/format.js'

const router = useRouter()
const comp = computed(() => store.comparison)
const callout = computed(() => hotelCallout(comp.value))
const hotelName = (id) => store.hotelsById[id]?.name ?? id
const fx = computed(() => store.fx)
// the server's summary sentences mention hotel ids; show names instead (numbers untouched)
const pretty = (t) => Object.entries(store.hotelsById).reduce((acc, [id, h]) => acc.split(id).join(h.name), t)
const results = computed(() => comp.value?.results ?? [])
const rank = (id) => comp.value?.ranking.find((r) => r.hotel_id === id)
const isBest = (id) => comp.value?.best_by_true_cost === id
const sgd = (id) => comp.value?.display_sgd?.[id]?.true_cost_sgd

function toggle(id) {
  const i = store.hotelIds.indexOf(id)
  if (i >= 0) store.hotelIds.splice(i, 1)
  else if (store.hotelIds.length < 3) store.hotelIds.push(id)
}

// value-of-time slider: reads the sensitivity grid the API already returned. No request per move.
const grid = computed(() => comp.value?.sensitivity?.grid ?? [])
const gridIdx = ref(0)
watch(grid, (g) => { const i = g.findIndex((x) => x.value_of_time_per_hour === Number(store.form.valueOfTime)); if (i >= 0) gridIdx.value = i })
const point = computed(() => grid.value[Math.min(gridIdx.value, Math.max(grid.value.length - 1, 0))] ?? null)
function use(id) { chooseHotel(id); router.push('/itinerary') }
onMounted(async () => {
  if (!store.hotelIds.length && store.hotelsById) store.hotelIds.push(...Object.keys(store.hotelsById))
  await ensureComparison()
  const i = grid.value.findIndex((g) => g.value_of_time_per_hour === Number(store.form.valueOfTime))
  gridIdx.value = i >= 0 ? i : 0
})
const errorsNow = computed(() => currentPrefs().errors)
</script>
<template>
  <div class="stack">
    <div>
      <h1>Compare hotels by true cost</h1>
      <p class="muted mb-0">True cost = rooms + admissions + estimated transport + travel time × the value you put on an hour + a charge for each optional sight left out. Hotels and rates are fictional.</p>
    </div>

    <fieldset class="card-soft">
      <legend class="h6">Hotels to compare (choose 2 or 3)</legend>
      <div class="d-flex flex-wrap gap-3">
        <div v-for="h in Object.values(store.hotelsById)" :key="h.id" class="form-check">
          <input :id="`h-${h.id}`" class="form-check-input" type="checkbox" :checked="store.hotelIds.includes(h.id)" @change="toggle(h.id)" />
          <label class="form-check-label" :for="`h-${h.id}`">{{ h.name }} <span class="muted">· {{ h.area }} · {{ formatJpy(h.nightly_rate) }}/night</span> <SourceBadge :status="h.source.record" what="rate" /></label>
        </div>
      </div>
      <div v-if="errorsNow.length" class="notice notice-warn mt-2" role="alert"><span class="glyph" aria-hidden="true">!</span><span>{{ errorsNow.join(' ') }} <router-link to="/">Fix the trip details</router-link></span></div>
      <button class="btn btn-primary mt-3" :disabled="store.busy.compare || rateLimited || store.hotelIds.length < 2 || errorsNow.length > 0" @click="runCompare" data-testid="compare">
        {{ store.busy.compare ? 'Comparing…' : comp ? 'Compare again' : 'Compare hotels' }}
      </button>
    </fieldset>

    <ErrorPanel v-if="store.comparisonError" :error="store.comparisonError" />
    <LoadingBlock v-if="store.busy.compare" text="Solving the best itinerary for each hotel… this can take several seconds." />

    <template v-if="comp && !store.busy.compare">
      <div v-if="callout.kind === 'differs'" class="notice notice-good" role="status" data-testid="callout-differs">
        <span class="glyph" aria-hidden="true">✓</span>
        <span><strong>{{ callout.text }}</strong> {{ hotelName(comp.cheapest_by_rate) }} has the lowest nightly rate, but {{ hotelName(comp.best_by_true_cost) }} has the lowest true cost.</span>
      </div>
      <div v-else-if="callout.kind === 'same'" class="notice notice-info" role="status" data-testid="callout-same">
        <span class="glyph" aria-hidden="true">i</span><span>{{ callout.text }} ({{ hotelName(comp.best_by_true_cost) }})</span>
      </div>
      <p v-if="comp.insight" class="mb-0" data-testid="insight">{{ comp.insight }}</p>

      <div class="notice notice-warn" v-if="comp.approximate || comp.partial" role="status" data-testid="approximate">
        <span class="glyph" aria-hidden="true">!</span>
        <span><strong>Approximate result.</strong> <template v-if="comp.partial">The overall time limit was reached, so not every hotel was solved. </template><template v-if="comp.approximate">At least one solve was not proven optimal, so a true cost may be higher than the best possible plan.</template></span>
      </div>

      <div class="card-soft table-responsive">
        <table class="table table-honest align-middle mb-0" data-testid="comparison-table">
          <caption class="text-start">True-cost calculation, line by line. Nights used: {{ comp.nights_used }} ({{ comp.nights_source }}). Value of time: {{ formatJpy(comp.value_of_time_per_hour) }}/hour. {{ comp.fx_label }}</caption>
          <thead>
            <tr><th scope="col">Line</th>
              <th v-for="r in results" :key="r.hotel_id" scope="col" class="num" :class="{ winner: isBest(r.hotel_id) }">
                {{ r.hotel_name }}
                <div class="fw-normal small">
                  <span v-if="isBest(r.hotel_id)" class="pill pill-must">Best overall</span>
                  <span v-if="comp.cheapest_by_rate === r.hotel_id" class="pill">Cheapest rate</span>
                </div>
              </th></tr>
          </thead>
          <tbody>
            <tr><th scope="row">Nightly rate <SourceBadge status="sample" what="rate" /></th><td v-for="r in results" :key="r.hotel_id" class="num">{{ formatJpy(r.nightly_rate_jpy) }}</td></tr>
            <tr><th scope="row">Rooms (rate × {{ comp.nights_used }} nights)</th><td v-for="r in results" :key="r.hotel_id" class="num">{{ r.breakdown ? formatJpy(r.breakdown.rooms_jpy) : 'n/a' }}</td></tr>
            <tr><th scope="row">Admissions (known prices)</th>
              <td v-for="r in results" :key="r.hotel_id" class="num">
                {{ r.breakdown ? formatJpy(r.breakdown.admissions_jpy) : 'n/a' }}
                <div v-if="r.breakdown?.unknown_price_items?.length" class="small muted">+ unknown: {{ r.breakdown.unknown_price_items.length }} sight(s) <SourceBadge :status="null" what="price" /></div>
              </td></tr>
            <tr><th scope="row">Transport <SourceBadge status="estimated" what="fares" /></th><td v-for="r in results" :key="r.hotel_id" class="num">{{ r.breakdown ? formatJpy(r.breakdown.transport_jpy) : 'n/a' }}</td></tr>
            <tr><th scope="row">Travel time × value of time</th>
              <td v-for="r in results" :key="r.hotel_id" class="num">
                <template v-if="r.breakdown">{{ formatJpy(r.breakdown.time_cost_jpy) }}<div class="small muted">{{ minutesToHm(r.breakdown.travel_minutes) }} (h:mm) × {{ formatJpy(r.breakdown.value_of_time_per_hour) }}/h</div></template>
                <template v-else>n/a</template>
              </td></tr>
            <tr><th scope="row">Missed preferences</th>
              <td v-for="r in results" :key="r.hotel_id" class="num">
                <template v-if="r.breakdown">{{ formatJpy(r.breakdown.missed_preferences.penalty_jpy) }}
                  <div class="small muted">{{ r.breakdown.missed_preferences.count }} × {{ formatJpy(r.breakdown.missed_preferences.penalty_per_item_jpy) }}<span v-if="r.breakdown.missed_preferences.names.length">: {{ r.breakdown.missed_preferences.names.join(', ') }}</span></div></template>
                <template v-else>n/a</template>
              </td></tr>
            <tr class="fw-bold"><th scope="row">True cost</th>
              <td v-for="r in results" :key="r.hotel_id" class="num" :class="{ winner: isBest(r.hotel_id) }" :data-testid="`true-cost-${r.hotel_id}`">
                <template v-if="r.breakdown">{{ formatJpy(r.breakdown.true_cost_jpy) }}<div class="small fw-normal muted">≈ {{ sgd(r.hotel_id) !== undefined ? `S$${sgd(r.hotel_id).toFixed(2)}` : UNKNOWN }} (sample rate)</div></template>
                <template v-else>n/a</template>
              </td></tr>
            <tr><th scope="row">Gap to the best</th><td v-for="r in results" :key="r.hotel_id" class="num">{{ rank(r.hotel_id) ? `${formatJpy(rank(r.hotel_id).gap_to_winner_jpy)}` : 'n/a' }}</td></tr>
            <tr><th scope="row">Solver status</th><td v-for="r in results" :key="r.hotel_id" class="num">{{ r.solver_status }}<span v-if="r.proven_optimal === false"> (not proven optimal)</span></td></tr>
            <tr><th scope="row">Independent validator</th><td v-for="r in results" :key="r.hotel_id" class="num">{{ r.validator_overall ? r.validator_overall.replace(/_/g, ' ') : 'n/a' }}</td></tr>
            <tr><th scope="row"><span class="sr-only">Actions</span></th>
              <td v-for="r in results" :key="r.hotel_id" class="num">
                <button v-if="r.feasible" class="btn btn-sm" :class="isBest(r.hotel_id) ? 'btn-primary' : 'btn-outline-primary'" @click="use(r.hotel_id)" :data-testid="`use-${r.hotel_id}`">Use this hotel</button>
                <span v-else>No feasible plan</span>
              </td></tr>
          </tbody>
        </table>
      </div>

      <div v-for="r in results.filter((x) => !x.feasible)" :key="r.hotel_id" class="notice notice-info" data-testid="hotel-infeasible">
        <span class="glyph" aria-hidden="true">i</span>
        <span><strong>{{ r.hotel_name }}:</strong> {{ r.status }}.
          <template v-if="r.conflicts?.length"><span v-for="(c, i) in r.conflicts" :key="i"> {{ c.message }}</span></template>
          <template v-else-if="r.note"> {{ r.note }}</template></span>
      </div>

      <section v-if="comp.warnings?.length" class="card-soft" aria-labelledby="warn-h" data-testid="warnings">
        <h2 id="warn-h" class="h6">Warnings from the planner (verbatim)</h2>
        <ul class="mb-0"><li v-for="w in comp.warnings" :key="w">{{ w }}</li></ul>
      </section>

      <LoadingBlock v-if="store.busy.sensitivity && !comp.sensitivity" text="The comparison above is ready. Working out how the ranking changes with your value of time… a few more seconds." />
      <div v-else-if="store.sensitivityError && !comp.sensitivity" class="notice notice-warn" data-testid="sensitivity-error">
        <span class="glyph" aria-hidden="true">!</span><span>The comparison above is complete, but the value-of-time analysis could not be loaded: {{ store.sensitivityError.display }}</span>
      </div>
      <section v-if="comp.sensitivity && grid.length" class="card-soft" aria-labelledby="vot-h" data-testid="sensitivity">
        <h2 id="vot-h" class="h5">What if your time is worth more or less?</h2>
        <p class="muted small">This uses values the server already computed ({{ comp.sensitivity.solves }} solves); moving the slider sends no request.</p>
        <label class="form-label" for="vot-grid">Value of time: <strong>{{ formatJpy(point.value_of_time_per_hour) }} / hour</strong></label>
        <input id="vot-grid" class="form-range" type="range" min="0" :max="grid.length - 1" step="1" v-model.number="gridIdx" :aria-valuetext="`${point.value_of_time_per_hour} yen per hour`" />
        <div data-testid="vot-point">
          Best at this value of time: <strong>{{ hotelName(point.winner) }}</strong>
          <span v-if="!point.exact" class="badge-src badge-estimated ms-1">approximate (upper bound)</span>
          <ul class="mb-2 mt-1">
            <li v-for="(cost, id) in point.true_cost_jpy" :key="id">{{ hotelName(id) }}: {{ formatJpy(cost) }} <span class="muted">(≈ {{ formatSgd(cost, fx?.jpy_per_sgd) }})</span></li>
          </ul>
        </div>
        <p class="mb-1" data-testid="flip-summary"><strong>{{ pretty(comp.sensitivity.flip_summary) }}</strong></p>
        <ul v-if="comp.sensitivity.flips.length" class="mb-1">
          <li v-for="f in comp.sensitivity.flips" :key="f.from_winner + f.value_of_time_per_hour">
            {{ hotelName(f.from_winner) }} → {{ hotelName(f.to_winner) }} at about {{ formatJpy(f.value_of_time_per_hour) }}/h
            <span v-if="f.method !== 'exact_crossing'" class="badge-src badge-estimated">approximate</span><span v-else class="badge-src badge-sample">exact crossing</span>
          </li>
        </ul>
        <p v-if="comp.sensitivity.approximate" class="small mb-0" style="color: var(--amber)"><span aria-hidden="true">!</span> The sensitivity analysis is approximate: {{ comp.sensitivity.warnings.join(' ') || 'values between solved points are bounds.' }}</p>
      </section>
    </template>
    <p v-else-if="!store.busy.compare && !store.comparisonError" class="muted" data-testid="compare-empty">Choose at least two hotels and press Compare.</p>
  </div>
</template>
