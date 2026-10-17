<script setup>
// Trip Trade-off Explorer. Every figure is from a real /compare-hotels (or /optimise) run on the planner; this component only displays and asks.
// Rooms, admissions and estimated transport are money. Travel time is shown in minutes AND as money at the chosen value of time. The score is not spending.
import { computed } from 'vue'
import { store, runExplorer, adoptExplorerPlan, restoreState, solverBusy, rateLimited } from '../store.js'
import { votOptions, entryRows, whyHotel } from '../lib/tradeoff.js'
import { formatLocalMoney } from '../lib/format.js'
import { cleanHotelText as ct } from '../lib/names.js'
import Hint from './Hint.vue'

const money = (v) => (v === null || v === undefined ? '—' : formatLocalMoney(v, store.city?.currency_code ?? 'JPY'))
const mins = (m) => (m === null || m === undefined ? '—' : m >= 60 ? `${Math.floor(m / 60)} h ${Math.round(m % 60)} min` : `${Math.round(m)} min`)
const options = computed(() => votOptions(store.city?.default_value_of_time_per_hour))
const current = computed(() => store.planPrefs?.value_of_time_per_hour ?? null)
const comp = computed(() => store.explorer.last ?? store.comparison)
const rows = computed(() => entryRows(comp.value?.baselines))
const why = computed(() => whyHotel(comp.value?.baselines, (v) => money(Math.abs(v)), mins))
const busy = computed(() => store.explorer.busy || solverBusy.value || rateLimited.value)
const exploredVot = computed(() => store.explorer.vot ?? current.value)
const best = computed(() => comp.value?.best_by_true_cost ?? null)
const hotelOf = (id) => ct(store.hotelsById?.[id]?.name ?? id)
const isNew = computed(() => store.explorer.last && best.value && (best.value !== store.chosenHotel || store.explorer.vot !== current.value))
</script>
<template>
  <section v-if="store.plan && store.planPrefs" class="card-soft" data-testid="explorer" aria-labelledby="explorer-h">
    <h2 id="explorer-h" class="h5 mb-1">Trade-off explorer</h2>
    <p class="muted small">How much is an hour of your time worth? Each button below re-runs the planner for real, with your locked stops and preferences kept. Hotels are demo hotels with sample prices; travel times are estimated from straight-line distances.</p>

    <div class="d-flex flex-wrap align-items-center gap-2 mb-2" role="group" aria-label="Value of an hour">
      <button v-for="o in options" :key="o.factor" type="button" class="btn btn-sm" :class="o.value === exploredVot ? 'btn-primary' : 'btn-outline-primary'"
        :disabled="busy" :data-testid="'explore-' + o.factor" @click="runExplorer(o.value)">{{ o.factor }}× · {{ money(o.value) }}/h</button>
      <span v-if="store.explorer.busy" class="small muted" role="status">Re-running the planner…</span>
    </div>
    <div v-if="store.explorer.error" class="notice notice-warn" role="alert" data-testid="explorer-error"><span class="glyph" aria-hidden="true">!</span><span>{{ store.explorer.error.message }}</span></div>

    <div v-if="rows.length" class="table-responsive">
      <table class="table table-sm align-middle mb-2" data-testid="explorer-table">
        <caption class="small muted">Value of an hour: {{ money(exploredVot) }}. Same sights, rules and routing for all three; only the hotel rule differs.</caption>
        <thead><tr><th>Plan</th><th>Hotel</th><th>Rooms</th><th>Admissions</th><th>Transport (est.)</th><th>Travel time (est.)</th><th>Travel time as money <Hint text="Minutes × the value of an hour. A way to weigh time against money, not something you pay." /></th><th>Optional sights left out</th><th>Score <Hint text="Spending + travel time as money + a charge for each optional sight left out. Lower is better. It is not what you pay." /></th></tr></thead>
        <tbody>
          <tr v-for="r in rows" :key="r.key" :data-testid="'row-' + r.key">
            <th scope="row">{{ r.label }}<span v-if="r.sameAs.length" class="small muted d-block">same hotel as {{ r.sameAs.join(', ') }}</span></th>
            <template v-if="r.feasible">
              <td>{{ ct(r.hotel) }}</td><td>{{ money(r.rooms) }}</td><td>{{ money(r.admissions) }}</td><td>{{ money(r.transport) }}</td>
              <td>{{ mins(r.minutes) }}</td><td>{{ money(r.timeValue) }}</td>
              <td>{{ r.omitted.length }}<span v-if="r.omitted.length" class="small muted"> ({{ money(r.charge) }})</span></td>
              <td><strong>{{ money(r.score) }}</strong></td>
            </template>
            <td v-else colspan="8">No feasible plan with this hotel rule.</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="rows.some((r) => r.unknown.length)" class="small muted" data-testid="explorer-unknown">Some sights have no known admission price; they are left out of the money columns (the planner values them with a placeholder inside the score only).</p>

    <div v-if="rows.length" data-testid="explorer-why">
      <p v-for="l in why.lines" :key="l" class="mb-1">{{ l }}</p>
      <p v-if="!why.change" class="small muted mb-1" data-testid="explorer-nochange">Nothing to trade off here: all three rules pick the same hotel.</p>
    </div>

    <div v-if="store.explorer.last" class="d-flex flex-wrap align-items-center gap-3 mt-2">
      <div class="form-check mb-0"><input id="keep-hotel" class="form-check-input" type="checkbox" v-model="store.explorer.keepHotel" data-testid="keep-hotel" /><label class="form-check-label" for="keep-hotel">Keep my hotel ({{ hotelOf(store.chosenHotel) }})</label></div>
      <button type="button" class="btn btn-sm btn-primary" :disabled="busy || !best" data-testid="adopt-explorer" @click="adoptExplorerPlan(best)">
        Use {{ store.explorer.keepHotel ? hotelOf(store.chosenHotel) : hotelOf(best) }} at {{ money(exploredVot) }}/h
      </button>
      <span v-if="!isNew" class="small muted">This is the plan you already have.</span>
    </div>

    <div v-if="store.explorer.runs.length > 1" class="mt-3" data-testid="explorer-runs">
      <h3 class="h6">Your explorer runs</h3>
      <ul class="small mb-0"><li v-for="r in store.explorer.runs" :key="r.vot">{{ money(r.vot) }}/h → best overall: <strong>{{ hotelOf(r.best) }}</strong></li></ul>
    </div>

    <div v-if="store.history.length > 1" class="mt-3" data-testid="plan-history">
      <h3 class="h6">Earlier plans <span class="muted fw-normal">(this session, in memory only)</span></h3>
      <ul class="list-unstyled small mb-0">
        <li v-for="h in store.history" :key="h.id" class="d-flex flex-wrap align-items-center gap-2 mb-1" :data-testid="'history-' + h.id">
          <span><strong>{{ h.label }}</strong> · {{ hotelOf(h.hotel) }} · {{ money(h.vot) }}/h<span v-if="h.travelMinutes !== null"> · {{ mins(h.travelMinutes) }} est. travel</span><span v-if="h.prefs?.locked?.length"> · {{ h.prefs.locked.length }} locked</span></span>
          <span v-if="h.plan === store.plan" class="pill">Showing now</span>
          <button v-else type="button" class="btn btn-sm btn-outline-secondary" :disabled="busy" :data-testid="'restore-' + h.id" @click="restoreState(h.id)">Show this plan</button>
        </li>
      </ul>
    </div>
  </section>
</template>
