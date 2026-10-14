<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import TripMap from '../components/TripMap.vue'
import SettingsSummaryStrip from '../components/SettingsSummaryStrip.vue'
import DayTimeline from '../components/DayTimeline.vue'
import FeasibilityReport from '../components/FeasibilityReport.vue'
import NotScheduledPanel from '../components/NotScheduledPanel.vue'
import ConflictPanel from '../components/ConflictPanel.vue'
import ErrorPanel from '../components/ErrorPanel.vue'
import LoadingBlock from '../components/LoadingBlock.vue'
import StopActions from '../components/StopActions.vue'
import PendingChanges from '../components/PendingChanges.vue'
import ProposedOperations from '../components/ProposedOperations.vue'
import DiffView from '../components/DiffView.vue'
import ExplainBlock from '../components/ExplainBlock.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { store, ensurePlan, runOptimise, applyAlternative, rateLimited, queueOp, unqueue, clearQueue, applyQueue, restorePrevious, explain } from '../store.js'
import { mustVisitRemovals } from '../lib/replan.js'
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
const lockedIds = computed(() => (store.planPrefs?.locked ?? []).map((l) => l.attraction_id))
const mustRemovals = computed(() => mustVisitRemovals(store.queue, store.planPrefs))
const confirmOpen = ref(false)
const names = (ids) => ids.map((id) => store.placesById[id]?.name ?? id).join(', ')
// The ONLY route to confirm_remove_must_visit = true is this dialog's confirm button.
function applyClicked() { mustRemovals.value.length ? (confirmOpen.value = true) : applyQueue({ confirmed: false }) }
function confirmed() { confirmOpen.value = false; applyQueue({ confirmed: true }) }
function selectStop({ attractionId }) {
  const target = document.getElementById(`timeline-stop-${attractionId}`)
  target?.scrollIntoView({ block: 'center' })
  target?.focus({ preventScroll: true })
}
const replan = computed(() => store.lastReplan)
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
    <SettingsSummaryStrip />

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

        <h2 class="sr-only">Map and day-by-day plan</h2>
        <div class="row g-3">
          <div class="col-12 col-lg-7"><TripMap :days="result.days" :hotel="hotel" :places-by-id="store.placesById" @select-stop="selectStop" /></div>
          <div class="col-12 col-lg-5"><DayTimeline :days="result.days" :places-by-id="store.placesById" :fx="store.fx" :hotel-name="hotel?.name ?? 'the hotel'" :locked-ids="lockedIds" :vot-per-hour="store.planPrefs?.value_of_time_per_hour ?? null">
            <template #actions="{ stop, day }">
              <StopActions :stop="stop" :day="day" :total-days="result.days.length" :name="store.placesById[stop.attraction_id]?.name ?? stop.attraction_id"
                :locked="lockedIds.includes(stop.attraction_id)" :disabled="store.busy.replan" @op="queueOp" />
            </template>
          </DayTimeline></div>
        </div>

        <FeasibilityReport :report="resp.feasibility_report" />
        <ExplainBlock :explanation="store.explanations.optimise" :busy="store.explaining === 'optimise'" :disabled="rateLimited || !!store.explaining" :error="store.explainError" @explain="explain('optimise')" />
        <NotScheduledPanel :missed-ids="result.missed_preferences" :places-by-id="store.placesById" :penalty-jpy="penalty" />

        <h2 class="mt-4">Change this plan</h2>
        <div v-if="store.restored" class="notice notice-good" role="status" data-testid="restored"><span class="glyph" aria-hidden="true">✓</span><span>The previous plan has been restored. It is the same result the planner gave you earlier; nothing was edited.</span></div>
        <div v-if="store.previous" class="notice notice-info" data-testid="restore-bar">
          <span class="glyph" aria-hidden="true">i</span><span>You are looking at a changed plan. <button type="button" class="btn btn-sm btn-outline-secondary ms-2" @click="restorePrevious" data-testid="restore-previous">Restore previous plan</button></span></div>
        <ErrorPanel v-if="store.replanError" :error="store.replanError" />
        <div v-if="store.lastReplan && store.lastReplan.status !== 'applied'" class="notice notice-info" data-testid="replan-unchanged" role="status">
          <span class="glyph" aria-hidden="true">i</span>
          <div class="w-100"><h3 class="h6 mb-1">Your original plan is unchanged</h3>
            <p class="mb-2">{{ store.lastReplan.summary }}</p>
            <ul v-if="store.lastReplan.conflicts?.length" class="mb-2" data-testid="replan-conflicts"><li v-for="(c, i) in store.lastReplan.conflicts" :key="i">{{ c.message }}</li></ul>
            <FeasibilityReport v-if="store.lastReplan.status === 'rejected_by_validator' && store.lastReplan.feasibility_report" :report="store.lastReplan.feasibility_report" />
            <p class="mb-0 small">The plan above is still the one in force. Your queued changes are kept so you can adjust or undo them.</p></div>
        </div>
        <PendingChanges :queue="store.queue" :places-by-id="store.placesById" :hotels-by-id="store.hotelsById" :hotel-choices="store.hotelIds" :current-hotel="store.chosenHotel"
          :busy="store.busy.replan" :disabled="rateLimited" :error="store.queueError" :budget-now="store.planPrefs?.budget ?? null" @op="queueOp" @remove="unqueue" @clear="clearQueue" @apply="applyClicked" />
        <ProposedOperations />
        <DiffView v-if="replan && replan.status === 'applied'" :result="replan" :places-by-id="store.placesById" />
        <ExplainBlock v-if="replan && replan.status === 'applied'" :explanation="store.explanations.replan" :busy="store.explaining === 'replan'" :disabled="rateLimited || !!store.explaining" :error="store.explainError" @explain="explain('replan')" />
        <ConfirmDialog :open="confirmOpen" title="Remove a must-visit?" confirm-label="Yes, remove it" cancel-label="Keep it in my plan" @cancel="confirmOpen = false" @confirm="confirmed">
          <p class="mb-2">You marked <strong>{{ names(mustRemovals) }}</strong> as a must-visit. Removing it means the new plan will no longer include something you said you required.</p>
          <p class="mb-0 small muted">Nothing is sent unless you confirm. The result will be labelled "Must-visit removed by user".</p>
        </ConfirmDialog>

        <section v-if="result.notes?.length" class="card-soft" data-testid="notes">
          <h2 class="h6">Notes from the planner</h2>
          <ul class="mb-0"><li v-for="n in result.notes" :key="n">{{ n }}</li></ul>
        </section>
      </template>
    </template>
  </div>
</template>
