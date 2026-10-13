<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import TripMap from '../components/TripMap.vue'
import DayTimeline from '../components/DayTimeline.vue'
import FeasibilityReport from '../components/FeasibilityReport.vue'
import NotScheduledPanel from '../components/NotScheduledPanel.vue'
import ConflictPanel from '../components/ConflictPanel.vue'
import ErrorPanel from '../components/ErrorPanel.vue'
import LoadingBlock from '../components/LoadingBlock.vue'
import { store, ensurePlan, runOptimise, applyAlternative, rateLimited } from '../store.js'
import { isInfeasible } from '../lib/rules.js'
import { formatJpy, formatMoney, humanMinutes, UNKNOWN } from '../lib/format.js'

const router = useRouter()
const resp = computed(() => store.plan)
const result = computed(() => resp.value?.result)
const hotel = computed(() => store.hotelsById[store.chosenHotel] ?? null)
const infeasible = computed(() => isInfeasible(resp.value))
const t = computed(() => result.value?.totals)
const penalty = computed(() => store.comparison?.missed_preference_penalty_jpy ?? null)
onMounted(() => { if (store.chosenHotel && store.places) ensurePlan() })
</script>
<template>
  <div class="stack">
    <div class="d-flex flex-wrap justify-content-between align-items-end gap-2">
      <div>
        <h1>Your itinerary</h1>
        <p class="muted mb-0" v-if="hotel">Base: <strong>{{ hotel.name }}</strong> <span class="pill">fictional hotel</span> · {{ hotel.area }}</p>
      </div>
      <div class="d-flex gap-2">
        <button class="btn btn-outline-secondary btn-sm" @click="router.push('/hotels')">Change hotel</button>
        <button class="btn btn-outline-primary btn-sm" :disabled="store.busy.optimise || rateLimited || !store.chosenHotel" @click="runOptimise">Recalculate</button>
      </div>
    </div>

    <div v-if="!store.chosenHotel" class="card-soft" data-testid="itinerary-empty">
      <p class="mb-2">No hotel chosen yet. Compare hotels, then press "Use this hotel".</p>
      <button class="btn btn-primary" @click="router.push('/hotels')">Go to hotel comparison</button>
    </div>
    <ErrorPanel v-if="store.planError" :error="store.planError" retryable @retry="runOptimise" />
    <LoadingBlock v-if="store.busy.optimise" text="Planning your days… a longer trip can take several seconds." />

    <template v-if="resp && !store.busy.optimise">
      <!-- infeasible is a NORMAL result: conflict panel, never the error component -->
      <template v-if="infeasible">
        <ConflictPanel :result="result" :prefs="store.planPrefs" :places-by-id="store.placesById" :busy="store.busy.optimise" :disabled="rateLimited" @apply="applyAlternative" />
        <FeasibilityReport :report="resp.feasibility_report" />
      </template>

      <template v-else>
        <div class="notice notice-warn" v-if="resp.approximate" role="status" data-testid="approximate">
          <span class="glyph" aria-hidden="true">!</span><span><strong>Approximate.</strong> {{ resp.approximate_note }}</span>
        </div>

        <section class="card-soft" aria-label="Totals" data-testid="totals">
          <div class="row g-3 text-center text-md-start">
            <div class="col-6 col-md-3"><div class="muted small">Sights scheduled</div><div class="kpi" data-testid="kpi-sights">{{ t.attractions_scheduled }}</div></div>
            <div class="col-6 col-md-3"><div class="muted small">Travel time</div><div class="kpi">{{ humanMinutes(t.travel_minutes) }}</div></div>
            <div class="col-6 col-md-3"><div class="muted small">Admissions</div><div class="kpi">{{ formatJpy(t.admissions_jpy) }}</div>
              <div v-if="t.unknown_cost_items.length" class="small" style="color: var(--amber)">+ {{ t.unknown_cost_items.length }} unknown price(s), not included</div></div>
            <div class="col-6 col-md-3"><div class="muted small">Transport <span class="badge-src badge-estimated">estimated</span></div><div class="kpi">{{ formatJpy(t.transport_jpy) }}</div></div>
          </div>
          <p class="mt-3 mb-0 small muted">
            Sights + transport: <strong>{{ formatMoney(t.total_jpy, store.fx) }}</strong>. Rooms are not included here ({{ resp.nights_used }} night(s), {{ resp.nights_source }}); see the hotel comparison.
            Solver: {{ result.solver_meta.solver_status }}<span v-if="result.solver_meta.solver_status !== 'OPTIMAL'"> (not proven optimal)</span>.
          </p>
        </section>

        <div class="row g-3">
          <div class="col-12 col-lg-7"><TripMap :days="result.days" :hotel="hotel" :places-by-id="store.placesById" /></div>
          <div class="col-12 col-lg-5"><DayTimeline :days="result.days" :places-by-id="store.placesById" :fx="store.fx" :hotel-name="hotel?.name ?? 'the hotel'" /></div>
        </div>

        <FeasibilityReport :report="resp.feasibility_report" />
        <NotScheduledPanel :missed-ids="result.missed_preferences" :places-by-id="store.placesById" :penalty-jpy="penalty" />

        <section v-if="result.notes?.length" class="card-soft" data-testid="notes">
          <h2 class="h6">Notes from the planner</h2>
          <ul class="mb-0"><li v-for="n in result.notes" :key="n">{{ n }}</li></ul>
        </section>
      </template>
    </template>
  </div>
</template>
