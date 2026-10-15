<script setup>
// "What if your time is worth more or less?" Runs ONLY when the user asks: it holds the server's single solver slot for several seconds.
// Shows elapsed time and a Cancel button while it runs. Once the values are back, the slider reads them locally (no request per move).
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import Hint from './Hint.vue'
import BusyNotice from './BusyNotice.vue'
import { store, runSensitivity, cancelSensitivity, rateLimited, solverBusy } from '../store.js'
import { formatDisplayMoney, formatLocalMoney } from '../lib/format.js'
import { cleanHotelText as ct } from '../lib/names.js'

const comp = computed(() => store.comparison)
const money = (v) => formatLocalMoney(v, store.city?.currency_code ?? 'JPY')
const display = (v) => formatDisplayMoney(v, store.city)
const hotelName = (id) => store.hotelsById[id]?.name ?? id
const pretty = (t) => ct(Object.entries(store.hotelsById).reduce((acc, [id, h]) => acc.split(id).join(h.name), t))
const grid = computed(() => comp.value?.sensitivity?.grid ?? [])
const gridIdx = ref(0)
watch(grid, (g) => { const i = g.findIndex((x) => x.value_of_time_per_hour === Number(store.form.valueOfTime)); gridIdx.value = i >= 0 ? i : 0 }, { immediate: true })
const point = computed(() => grid.value[Math.min(gridIdx.value, Math.max(grid.value.length - 1, 0))] ?? null)
const elapsed = ref(0)
let timer = null
watch(() => store.busy.sensitivity, (on) => {
  clearInterval(timer)
  if (on) { elapsed.value = 0; timer = setInterval(() => { elapsed.value = Math.round((Date.now() - store.sensitivityStartedAt) / 1000) }, 1000) }
}, { immediate: true })
onBeforeUnmount(() => clearInterval(timer))
</script>
<template>
  <section v-if="comp" class="card-soft" aria-labelledby="vot-h" data-testid="sensitivity-section">
    <h2 id="vot-h" class="h5">What if your time is worth more or less?</h2>
    <template v-if="!comp.sensitivity">
      <p class="muted small mb-2">This re-solves each hotel at many values of an hour of your time to find where the best hotel changes. It uses the planner for several seconds, so it only runs when you ask.</p>
      <div class="d-flex flex-wrap align-items-center gap-2">
        <button type="button" class="btn btn-outline-primary" :disabled="solverBusy || rateLimited" @click="runSensitivity" data-testid="run-sensitivity">See how your value of time changes the winner</button>
        <span v-if="store.busy.sensitivity" class="d-inline-flex align-items-center gap-2" role="status" aria-live="polite" data-testid="sens-progress">
          <span class="spinner" aria-hidden="true"></span> Working… {{ elapsed }} s <Hint text="This holds the solver for several seconds, so other plan actions wait until it finishes or you cancel." />
          <button type="button" class="btn btn-sm btn-outline-secondary" @click="cancelSensitivity" data-testid="cancel-sens">Cancel</button>
        </span>
      </div>
      <BusyNotice :error="store.sensitivityError" class="mt-2" @retry="runSensitivity" />
      <div v-if="store.sensitivityCancelled && !store.busy.sensitivity" class="notice notice-warn mt-2" data-testid="sens-cancelled"><span class="glyph" aria-hidden="true">!</span><span>Cancelled. Your plan and the comparison are unchanged.</span></div>
      <div v-else-if="store.sensitivityError && store.sensitivityError.code !== 'solver_busy' && !store.busy.sensitivity" class="notice notice-warn mt-2" data-testid="sensitivity-error"><span class="glyph" aria-hidden="true">!</span><span>The analysis could not be loaded: {{ store.sensitivityError.display ?? store.sensitivityError.message }}</span></div>
    </template>
    <div v-else-if="grid.length && point" data-testid="sensitivity">
      <p class="muted small">Uses values already computed ({{ comp.sensitivity.solves }} solves); the slider sends no request.</p>
      <label class="form-label" for="vot-grid">Value of time: <strong>{{ money(point.value_of_time_per_hour) }} / hour</strong></label>
      <input id="vot-grid" class="form-range" type="range" min="0" :max="grid.length - 1" step="1" v-model.number="gridIdx" :aria-valuetext="`${point.value_of_time_per_hour} ${store.city?.currency_code ?? 'local currency'} per hour`" />
      <div data-testid="vot-point">
        Best at this value of time: <strong>{{ hotelName(point.winner) }}</strong>
        <span v-if="!point.exact" class="badge-src badge-estimated ms-1">approximate (upper bound)</span>
        <ul class="mb-2 mt-1"><li v-for="(cost, id) in point.true_cost_jpy" :key="id">{{ hotelName(id) }}: {{ money(cost) }} <span class="muted">(≈ {{ display(cost) }})</span></li></ul>
      </div>
      <p class="mb-1" data-testid="flip-summary"><strong>{{ pretty(comp.sensitivity.flip_summary) }}</strong></p>
      <ul v-if="comp.sensitivity.flips.length" class="mb-1">
        <li v-for="f in comp.sensitivity.flips" :key="f.from_winner + f.value_of_time_per_hour">
          {{ hotelName(f.from_winner) }} → {{ hotelName(f.to_winner) }} at about {{ money(f.value_of_time_per_hour) }}/h
          <span v-if="f.method !== 'exact_crossing'" class="badge-src badge-estimated">approximate</span><span v-else class="badge-src badge-sample">exact crossing</span>
        </li>
      </ul>
      <p v-if="comp.sensitivity.approximate" class="small mb-0" style="color: var(--amber)"><span aria-hidden="true">!</span> The sensitivity analysis is approximate: {{ comp.sensitivity.warnings.join(' ') || 'values between solved points are bounds.' }}</p>
    </div>
  </section>
</template>
