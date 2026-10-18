<script setup>
// "Compare hotels": the full generalised-cost breakdown for the compared hotels, one column per hotel. Expandable; the verdict above it is always visible.
import { costTerms } from '../lib/costTerms.js'
import { computed } from 'vue'
import SourceBadge from './SourceBadge.vue'
import ExplainBlock from './ExplainBlock.vue'
import { topWarnings } from '../lib/band.js'
import { store, explain, rateLimited, switchHotel, solverBusy } from '../store.js'
import { formatDisplayMoney, formatLocalMoney, minutesToHm, UNKNOWN } from '../lib/format.js'
import { cleanHotelText as ct } from '../lib/names.js'
import { categoryOf } from '../lib/conflicts.js'

const comp = computed(() => store.comparison)
const money = (v) => formatLocalMoney(v, store.city?.currency_code ?? 'JPY')
const display = (v) => formatDisplayMoney(v, store.city)
const pretty = (t) => costTerms(ct(Object.entries(store.hotelsById).reduce((acc, [id, h]) => acc.split(id).join(h.name), t)))
const results = computed(() => comp.value?.results ?? [])
const warnings = computed(() => topWarnings((comp.value?.warnings ?? []).map(pretty)))
const rank = (id) => comp.value?.ranking.find((r) => r.hotel_id === id)
const isBest = (id) => comp.value?.best_by_true_cost === id
const displayCost = (id) => comp.value?.display_values?.[id]?.true_cost
</script>
<template>
  <details v-if="comp" class="card-soft compare-details" data-testid="compare-details">
    <summary class="fw-semibold">Compare hotels: the full generalised-cost breakdown</summary>
    <div class="stack mt-3">
      <div class="table-responsive">
        <table class="table table-honest align-middle mb-0" data-testid="comparison-table">
          <caption class="text-start">Generalised-cost calculation, line by line. Nights used: {{ comp.nights_used }} ({{ comp.nights_source }}). Value of time: {{ money(comp.value_of_time_per_hour) }}/hour. {{ comp.display_fx_label || comp.fx_label }}</caption>
          <thead>
            <tr><th scope="col">Line</th>
              <th v-for="r in results" :key="r.hotel_id" scope="col" class="num" :class="{ winner: isBest(r.hotel_id) }">
                {{ ct(r.hotel_name) }}
                <div class="fw-normal small">
                  <span v-if="isBest(r.hotel_id)" class="pill pill-must">Lowest modelled score</span>
                  <span v-if="comp.cheapest_by_rate === r.hotel_id" class="pill">Cheapest rate</span>
                </div>
              </th></tr>
          </thead>
          <tbody>
            <tr><th scope="row">Nightly rate <SourceBadge status="sample" what="rate" /></th><td v-for="r in results" :key="r.hotel_id" class="num">{{ money(r.nightly_rate_jpy) }}</td></tr>
            <tr><th scope="row">Rooms (rate × {{ comp.nights_used }} nights)</th><td v-for="r in results" :key="r.hotel_id" class="num">{{ r.breakdown ? money(r.breakdown.rooms_jpy) : 'n/a' }}</td></tr>
            <tr><th scope="row">Admissions (known prices)</th>
              <td v-for="r in results" :key="r.hotel_id" class="num">
                {{ r.breakdown ? money(r.breakdown.admissions_jpy) : 'n/a' }}
                <div v-if="r.breakdown?.unknown_price_items?.length" class="small muted">+ unknown: {{ r.breakdown.unknown_price_items.length }} sight(s) <SourceBadge :status="null" what="price" /></div>
              </td></tr>
            <tr><th scope="row">Transport <SourceBadge status="estimated" what="fares" /></th><td v-for="r in results" :key="r.hotel_id" class="num">{{ r.breakdown ? money(r.breakdown.transport_jpy) : 'n/a' }}</td></tr>
            <tr><th scope="row">Travel time × value of time</th>
              <td v-for="r in results" :key="r.hotel_id" class="num">
                <template v-if="r.breakdown">{{ money(r.breakdown.time_cost_jpy) }}<div class="small muted">{{ minutesToHm(r.breakdown.travel_minutes) }} (h:mm) × {{ money(r.breakdown.value_of_time_per_hour) }}/h</div></template>
                <template v-else>n/a</template>
              </td></tr>
            <tr><th scope="row">Missed preferences</th>
              <td v-for="r in results" :key="r.hotel_id" class="num">
                <template v-if="r.breakdown">{{ money(r.breakdown.missed_preferences.penalty_jpy) }}
                  <div class="small muted">{{ r.breakdown.missed_preferences.count }} × {{ money(r.breakdown.missed_preferences.penalty_per_item_jpy) }}<span v-if="r.breakdown.missed_preferences.names.length">: {{ r.breakdown.missed_preferences.names.join(', ') }}</span></div></template>
                <template v-else>n/a</template>
              </td></tr>
            <tr class="fw-bold"><th scope="row">Generalised cost <span class="small fw-normal muted d-block">not money spent</span></th>
              <td v-for="r in results" :key="r.hotel_id" class="num" :class="{ winner: isBest(r.hotel_id) }" :data-testid="`true-cost-${r.hotel_id}`">
                <template v-if="r.breakdown">{{ money(r.breakdown.true_cost_jpy) }}<div class="small fw-normal muted">≈ {{ displayCost(r.hotel_id) !== undefined ? `${displayCost(r.hotel_id).toFixed(2)} ${comp.display_currency}` : display(r.breakdown.true_cost_jpy) || UNKNOWN }} (sample rate)</div></template>
                <template v-else>n/a</template>
              </td></tr>
            <tr><th scope="row">Gap to the best</th><td v-for="r in results" :key="r.hotel_id" class="num">{{ rank(r.hotel_id) ? `${money(rank(r.hotel_id).gap_to_winner_jpy)}` : 'n/a' }}</td></tr>
            <tr><th scope="row">Solver status</th><td v-for="r in results" :key="r.hotel_id" class="num">{{ r.solver_status }}<span v-if="r.proven_optimal === false"> (not proven optimal)</span></td></tr>
            <tr><th scope="row">Independent validator</th><td v-for="r in results" :key="r.hotel_id" class="num">{{ r.validator_overall ? r.validator_overall.replace(/_/g, ' ') : 'n/a' }}</td></tr>
            <tr><th scope="row"><span class="sr-only">Actions</span></th>
              <td v-for="r in results" :key="r.hotel_id" class="num">
                <span v-if="store.chosenHotel === r.hotel_id" class="pill">In your plan</span>
                <button v-else-if="r.feasible" class="btn btn-sm" :class="isBest(r.hotel_id) ? 'btn-primary' : 'btn-outline-primary'" :disabled="solverBusy || rateLimited" @click="switchHotel(r.hotel_id)" :data-testid="`use-${r.hotel_id}`">Use this hotel</button>
                <span v-else>{{ (r.conflicts?.length && r.conflicts.every((c) => categoryOf(c) === 'missing_information')) ? 'Blocked by missing information' : 'No feasible plan' }}</span>
              </td></tr>
          </tbody>
        </table>
      </div>
      <div v-for="r in results.filter((x) => !x.feasible)" :key="r.hotel_id" class="notice notice-info" data-testid="hotel-infeasible">
        <span class="glyph" aria-hidden="true">i</span>
        <span><strong>{{ ct(r.hotel_name) }}:</strong> {{ r.status }}.
          <template v-if="r.conflicts?.length"><span v-for="(c, i) in r.conflicts" :key="i"> {{ pretty(c.message) }}</span></template>
          <template v-else-if="r.note"> {{ pretty(r.note) }}</template></span>
      </div>
      <ExplainBlock title="Explain the hotel comparison" :explanation="store.explanations.compare" :busy="store.explaining === 'compare'" :disabled="rateLimited || !!store.explaining" :error="store.explainError" @explain="explain('compare')" />
      <section v-if="comp.warnings?.length" aria-labelledby="warn-h" data-testid="warnings">
        <h2 id="warn-h" class="h6">Warnings from the planner</h2>
        <ul class="mb-0"><li v-for="w in warnings.shown" :key="w">{{ w }}</li></ul>
        <details v-if="warnings.more.length" class="mt-1"><summary>Show {{ warnings.more.length }} more</summary><ul class="mb-0 mt-1"><li v-for="w in warnings.more" :key="w">{{ w }}</li></ul></details>
      </section>
    </div>
  </details>
</template>
