<script setup>
// The cost panel. Every figure comes from the server's cost_summary (same numbers the validator checks) or the hotel comparison; this component only
// lays them out. Two different figures are kept apart on purpose: CASH cost (money spent) and TRUE cost (cash plus the value of your time, used only
// to compare hotels, never money). Unknown prices are listed and are never counted as zero.
import { computed } from 'vue'
import Hint from './Hint.vue'
import { formatCash, formatLocalMoney } from '../lib/format.js'
import { store } from '../store.js'

const cs = computed(() => store.plan?.cost_summary ?? null)
const cur = computed(() => cs.value?.currency ?? store.city?.currency_code ?? 'JPY')
const money = (v) => formatLocalMoney(v, cur.value)
const maxDay = computed(() => Math.max(1, ...(cs.value?.days ?? []).map((d) => d.day_total)))
const pct = (v) => `${Math.round((v / maxDay.value) * 100)}%`
const names = (ids) => ids.map((id) => store.placesById[id]?.name ?? id)
const budget = computed(() => store.planPrefs?.budget ?? null)
const strict = computed(() => !!store.planPrefs?.strict_budget)
const spent = computed(() => cs.value?.trip.cash_total ?? 0)
const over = computed(() => (budget.value !== null && spent.value > budget.value ? spent.value - budget.value : 0))
const budgetPct = computed(() => (budget.value ? Math.min(100, Math.round((spent.value / budget.value) * 100)) : 0))
// True cost for the hotel in the plan: from the comparison (or the replan diff when the plan was changed). It is a comparison figure, never labelled as money.
const trueCost = computed(() => {
  if (store.planFromReplan) return store.lastReplan?.diff?.true_cost_jpy?.after ?? null
  const r = store.comparison?.results?.find((x) => x.hotel_id === store.chosenHotel)
  return r?.breakdown?.true_cost_jpy ?? null
})
</script>
<template>
  <section v-if="cs" class="card-soft cost-panel" aria-labelledby="cost-h" data-testid="cost-panel">
    <h2 id="cost-h" class="h5">Your modelled spending</h2>
    <dl class="spending-cards">
      <div><dt>Demo hotel rooms</dt><dd>{{ money(cs.trip.rooms) }}</dd><span class="small muted">{{ money(cs.trip.nightly_rate) }} × {{ cs.trip.nights }} nights</span></div>
      <div><dt>Known admissions</dt><dd>{{ money(cs.trip.admissions) }}</dd></div>
      <div><dt>Estimated transport</dt><dd>{{ money(cs.trip.transport) }}</dd></div>
      <div><dt>Modelled cash incl. rooms</dt><dd>{{ money(cs.trip.cash_total_with_rooms) }}</dd></div>
    </dl>
    <details data-testid="cash-breakdown"><summary>View detailed breakdown</summary><div class="table-responsive mt-3">
      <table class="table table-honest align-middle mb-2" style="min-width:30rem" data-testid="cost-table">
        <caption class="sr-only">Cash cost per day: admissions, transport and the day total, in {{ cur }}.</caption>
        <thead><tr><th scope="col">Day</th><th scope="col" class="num">Admissions</th><th scope="col" class="num">Transport</th><th scope="col" class="num">Day total</th><th scope="col"><span class="sr-only">Share of the largest day</span></th></tr></thead>
        <tbody>
          <tr v-for="d in cs.days" :key="d.day" :data-testid="`cost-day-${d.day}`">
            <th scope="row">Day {{ d.day }}</th>
            <td class="num">{{ d.admissions === 0 && !d.unknown_price_ids.length ? 'Free' : money(d.admissions) }}<div v-if="d.unknown_price_ids.length" class="small muted">+ {{ d.unknown_price_ids.length }} price(s) unknown</div></td>
            <td class="num">{{ money(d.transport) }}</td>
            <td class="num fw-bold">{{ money(d.day_total) }}</td>
            <td style="min-width:5rem"><div class="mini-bar" aria-hidden="true"><div class="mini-bar-fill" :style="{ width: pct(d.day_total) }"></div></div></td>
          </tr>
          <tr data-testid="cost-subtotal"><th scope="row">Sights and transport</th><td class="num">{{ cs.trip.admissions === 0 && !cs.trip.unknown_price_count ? 'Free' : money(cs.trip.admissions) }}</td><td class="num">{{ money(cs.trip.transport) }}</td><td class="num fw-bold">{{ money(cs.trip.cash_total) }}</td><td></td></tr>
          <tr data-testid="cost-rooms"><th scope="row">Rooms <span class="small fw-normal muted">({{ money(cs.trip.nightly_rate) }} × {{ cs.trip.nights }} {{ cs.trip.nights === 1 ? 'night' : 'nights' }})</span></th><td></td><td></td><td class="num fw-bold">{{ money(cs.trip.rooms) }}</td><td></td></tr>
          <tr class="fw-bold" data-testid="cost-trip-total"><th scope="row">Trip total in cash</th><td></td><td></td><td class="num" data-testid="trip-cash-total">{{ money(cs.trip.cash_total_with_rooms) }}</td><td></td></tr>
        </tbody>
      </table>
    </div></details>
    <p v-if="cs.trip.unknown_price_count" class="small mb-2" style="color: var(--amber)" data-testid="cost-unknown"><span aria-hidden="true">!</span> {{ cs.trip.unknown_price_count }} {{ cs.trip.unknown_price_count === 1 ? 'price is' : 'prices are' }} unknown, not included: {{ names(cs.trip.unknown_price_ids).join(', ') }}.</p>

    <div v-if="budget !== null" class="mb-2" data-testid="budget-meter">
      <div class="d-flex flex-wrap justify-content-between gap-1 small"><span><strong>Budget</strong> {{ money(budget) }} ({{ strict ? 'strict limit' : 'target' }})</span><span :class="over ? 'text-danger fw-bold' : ''">{{ over ? `Over by ${money(over)}` : `${money(budget - spent)} left` }}</span></div>
      <div class="budget-track" role="meter" :aria-valuemin="0" :aria-valuemax="budget" :aria-valuenow="Math.min(spent, budget)" :aria-valuetext="`${money(spent)} of ${money(budget)}`"><div class="budget-fill" :class="{ over: over > 0 }" :style="{ width: budgetPct + '%' }"></div></div>
      <p class="small muted mb-0">The budget covers sights and transport only (not rooms or food): {{ money(spent) }} of {{ money(budget) }}.</p>
    </div>

    <dl class="two-figures small mb-0" data-testid="two-figures">
      <div><dt>Cash cost <Hint text="Money you would spend: admissions and estimated transport (and rooms where shown). Sample data, not a quote." label="What is cash cost?" /></dt>
        <dd data-testid="figure-cash">{{ money(cs.trip.cash_total) }} for sights and transport · {{ money(cs.trip.cash_total_with_rooms) }} with rooms</dd></div>
      <div v-if="trueCost !== null"><dt>Generalised cost <Hint text="Cash cost plus the value of your travel time (at the rate you set) and a charge for optional sights left out. It exists only to compare plans and hotels. It is not money you spend." label="What is generalised cost?" /></dt>
        <dd data-testid="figure-true">{{ formatCash(trueCost, cur) }} <span class="muted">(a comparison figure, not money)</span></dd></div>
    </dl>
  </section>
</template>
