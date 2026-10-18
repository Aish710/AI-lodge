<script setup>
// Screen 2 of 2: the plan. The hotel is switched here, in place; the old plan stays visible (dimmed) until the new one arrives, and a failure never blanks it.
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import TripCopilot from '../components/TripCopilot.vue'
import TripMap from '../components/TripMap.vue'
import SettingsSummaryStrip from '../components/SettingsSummaryStrip.vue'
import DayTimeline from '../components/DayTimeline.vue'
import FeasibilityReport from '../components/FeasibilityReport.vue'
import NotScheduledPanel from '../components/NotScheduledPanel.vue'
import ConflictPanel from '../components/ConflictPanel.vue'
import ErrorPanel from '../components/ErrorPanel.vue'
import StopActions from '../components/StopActions.vue'
import PendingChanges from '../components/PendingChanges.vue'
import ProposedOperations from '../components/ProposedOperations.vue'
import DiffView from '../components/DiffView.vue'
import ExplainBlock from '../components/ExplainBlock.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import Hint from '../components/Hint.vue'
import HowMade from '../components/HowMade.vue'
import StatusChip from '../components/StatusChip.vue'
import HotelSwitch from '../components/HotelSwitch.vue'
import PlanProgress from '../components/PlanProgress.vue'
import BusyNotice from '../components/BusyNotice.vue'
import CompareDetails from '../components/CompareDetails.vue'
import SensitivityPanel from '../components/SensitivityPanel.vue'
import GettingAround from '../components/GettingAround.vue'
import CostPanel from '../components/CostPanel.vue'
import TradeoffExplorer from '../components/TradeoffExplorer.vue'
import ItineraryCompare from '../components/ItineraryCompare.vue'
import WhatIfPanel from '../components/WhatIfPanel.vue'
import BenefitStrip from '../components/BenefitStrip.vue'
import RepairAssistant from '../components/RepairAssistant.vue'
import DaySelector from '../components/DaySelector.vue'
import AiMark from '../components/AiMark.vue'
import AiLegend from '../components/AiLegend.vue'
import { checksTally, hotelVerdict, planStatus, sightsCovered } from '../lib/band.js'
import { store, runOptimise, switchHotel, applyAlternative, rateLimited, solverBusy, queueOp, unqueue, clearQueue, applyQueue, restorePrevious, explain, resetAll } from '../store.js'
import { mustVisitRemovals } from '../lib/replan.js'
import { hotelCallout, isInfeasible } from '../lib/rules.js'
import { formatLocalMoney, formatMoney, humanMinutes } from '../lib/format.js'
import { planSummary } from '../lib/planSummary.js'
import { money } from '../lib/money.js'
import { cleanHotelText as ct } from '../lib/names.js'

const router = useRouter()
const resp = computed(() => store.plan)
const result = computed(() => resp.value?.result)
const hotel = computed(() => store.hotelsById[store.chosenHotel] ?? null)
const infeasible = computed(() => isInfeasible(resp.value))
const t = computed(() => result.value?.totals)
const cash = computed(() => resp.value?.cost_summary?.trip ?? null)
const summary = computed(() => planSummary(resp.value, { money, mins: humanMinutes, names: Object.fromEntries(Object.entries(store.placesById).map(([k, v]) => [k, v.name])), hotelName: hotel.value?.name ?? '', wanted: cover.value.wanted }))
const activeDays = computed(() => (result.value?.days ?? []).filter((d) => d.stops?.length).length)
const status = computed(() => planStatus(resp.value))
const tally = computed(() => checksTally(resp.value?.feasibility_report))
const cover = computed(() => sightsCovered(t.value?.attractions_scheduled ?? 0, store.places, store.wishlist))
const penalty = computed(() => store.comparison?.missed_preference_penalty_jpy ?? null)
const comp = computed(() => store.comparison)
const verdict = computed(() => hotelVerdict(comp.value, (v) => formatLocalMoney(v, store.city?.currency_code ?? 'JPY')))
const callout = computed(() => hotelCallout(comp.value))
const pretty = (t) => ct(Object.entries(store.hotelsById).reduce((acc, [id, h]) => acc.split(id).join(h.name), t))
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
const busyError = computed(() => (store.planError?.code === 'solver_busy' ? store.planError : store.replanError?.code === 'solver_busy' ? store.replanError : null))
const realPlanError = computed(() => (store.planError && store.planError.code !== 'solver_busy' ? store.planError : null))
const realReplanError = computed(() => (store.replanError && store.replanError.code !== 'solver_busy' ? store.replanError : null))
// Retry is always MANUAL. It repeats the action that was refused: the hotel switch if one was pending, otherwise a fresh plan for the current hotel.
function retry() { store.pendingHotel ? switchHotel(store.pendingHotel) : runOptimise() }
function startOver() {
  if (!window.confirm('Clear this trip and start over?')) return
  resetAll()
  router.push('/')
}
const planning = computed(() => store.busy.optimise || store.busy.compare)
const activeStop = ref(null)   // card <-> pin link: hovering or focusing one highlights the other
</script>
<template>
  <div class="stack">
    <div class="d-flex flex-wrap justify-content-between align-items-end gap-2">
      <div>
        <h1>Your trip</h1>
        <p class="muted mb-0" v-if="hotel">Base: <strong>{{ hotel.name }}</strong> <span class="pill" title="A made-up hotel with a sample price">Demo hotel</span> · {{ hotel.area }}</p>
      </div>
      <div class="d-flex flex-wrap gap-2">
        <button class="btn btn-outline-primary btn-sm" @click="router.push('/')" data-testid="edit-trip">Edit trip</button>
        <button class="btn btn-outline-secondary btn-sm" :disabled="planning || solverBusy || rateLimited || !store.chosenHotel" @click="runOptimise()">Recalculate</button>
        <button class="btn btn-link btn-sm" @click="startOver" data-testid="start-over">Start over</button>
      </div>
    </div>
    <SettingsSummaryStrip />
    <AiLegend v-if="resp" />

    <div v-if="!resp && !planning" class="card-soft" data-testid="itinerary-empty">
      <p class="mb-2">No plan yet. Choose your sights on the Plan screen and press "Plan my trip".</p>
      <button class="btn btn-primary" @click="router.push('/')" data-testid="go-plan">Go to Plan</button>
    </div>
    <BusyNotice :error="busyError" @retry="retry" />
    <ErrorPanel v-if="realPlanError" :error="realPlanError" retryable @retry="retry" />
    <PlanProgress switching />

    <template v-if="resp">
      <HotelSwitch />
      <TripCopilot />
      <div v-if="!infeasible" data-testid="copilot-repair" tabindex="-1" class="card-soft"><RepairAssistant /></div>
      <div :class="{ dimmed: planning }" :aria-busy="planning" data-testid="trip-body">
        <div class="stack">
          <!-- infeasible is a NORMAL result: conflict panel, never the error component -->
          <template v-if="infeasible">
            <StatusChip v-bind="status" />
            <div data-testid="copilot-repair" tabindex="-1"><ConflictPanel :result="result" :prefs="store.planPrefs" :places-by-id="store.placesById" :busy="store.busy.optimise" :disabled="rateLimited || solverBusy" @apply="applyAlternative">
              <template #assistant><RepairAssistant /></template>
            </ConflictPanel></div>
            <FeasibilityReport :report="resp.feasibility_report" />
          </template>

          <template v-else>
            <div v-if="resp.feasibility_report?.verification === 'conditional'" class="notice notice-warn" role="status" data-testid="conditional-banner">
              <span class="glyph" aria-hidden="true">!</span>
              <span><strong>Provisional plan. Opening hours unverified.</strong> This plan is feasible only if {{ (resp.feasibility_report.conditional_stop_ids ?? []).map((id) => store.placesById[id]?.name ?? id).join(', ') }} {{ (resp.feasibility_report.conditional_stop_ids ?? []).length === 1 ? 'is' : 'are' }} open at the scheduled time; the sample data does not say. Check the opening hours before you travel. It is not a verified itinerary.</span>
            </div>
            <section v-if="verdict" class="card-soft" :class="`verdict-${verdict.kind}`" data-testid="verdict" aria-live="polite">
              <div class="verdict">{{ verdict.headline }} <AiMark kind="calc" /></div>
              <div class="verdict-detail">{{ verdict.detail }}</div>
              <HowMade class="mt-2" :explained="store.explanations.compare?.source ?? null" />
            </section>
            <div v-if="callout.kind === 'differs'" class="notice notice-good" role="status" data-testid="callout-differs"><span class="glyph" aria-hidden="true">✓</span><span><strong>{{ callout.text }}</strong></span></div>
            <details v-if="comp?.insight" class="small" data-testid="insight-details"><summary>Why?</summary><p class="mb-0 mt-1" data-testid="insight">{{ pretty(comp.insight) }}</p></details>
            <ExplainBlock :summary="summary" :days="result.days" :explanation="store.explanations.optimise" :busy="store.explaining === 'optimise'" :disabled="rateLimited || !!store.explaining" :error="store.explainError" @explain="explain('optimise')" />
            <ProposedOperations />
            <div class="notice notice-warn" v-if="resp.approximate || comp?.approximate || comp?.partial" role="status" data-testid="approximate">
              <span class="glyph" aria-hidden="true">!</span><span><strong>Approximate.</strong> {{ resp.approximate ? resp.approximate_note : 'The comparison was not fully proven optimal, so a true cost may be higher than the best possible plan.' }}</span>
            </div>

            <section class="band" aria-label="Plan summary" data-testid="totals">
              <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
                <StatusChip v-bind="status" /><AiMark kind="calc" />
                <HowMade :explained="store.explanations.optimise?.source ?? null" />
              </div>
              <div class="row g-3">
                <div class="col-12 col-lg-8"><div class="row g-3">
                <div class="col-6"><div class="tile">
                  <div class="tile-label">Estimated spending incl. rooms <Hint text="Modelled cash: admissions with a known price + estimated transport + the demo hotel's rooms at its sample rate. Unknown prices are excluded, not free. Not a quote and not the generalised cost. A budget you set covers sights and transport only, not rooms." label="What does estimated spending include?" /></div>
                  <div class="tile-value" data-testid="kpi-total">{{ money(cash?.cash_total_with_rooms ?? t.total_jpy) }}</div>
                  <div class="tile-sub" data-testid="kpi-total-parts">sights and transport {{ money(t.total_jpy) }}<template v-if="cash"> + rooms {{ money(cash.rooms) }} ({{ cash.nights }} night{{ cash.nights === 1 ? '' : 's' }})</template></div></div></div>
                <div class="col-6"><div class="tile">
                  <div class="tile-label">Travel time, all days (estimated) <Hint text="Time moving between places, not time at sights." label="What does travel time mean?" /></div>
                  <div class="tile-value" data-testid="kpi-travel">{{ humanMinutes(t.travel_minutes) }}</div></div></div>
                <div class="col-6"><div class="tile">
                  <div class="tile-label">Sights covered <Hint text="Sights in the plan, out of the sights you did not mark 'not interested'." label="What does sights covered mean?" /></div>
                  <div class="tile-value" data-testid="kpi-sights">{{ cover.scheduled }} of {{ cover.wanted }}</div></div></div>
                <div class="col-6"><div class="tile">
                  <div class="tile-label">Checks passed <Hint text="The independent validator re-checks every rule on the finished plan." label="What are the checks?" /></div>
                  <div class="tile-value" data-testid="kpi-checks">{{ tally.passed }} of {{ tally.total }}</div></div></div>
                </div></div>
                <div class="col-12 col-lg-4"><GettingAround /></div>
              </div>
              <p class="mt-2 mb-0 small muted">
                Admissions {{ money(t.admissions_jpy) }} + transport {{ money(t.transport_jpy) }} <span class="badge-src badge-estimated">estimated</span><template v-if="cash"> + rooms {{ money(cash.rooms) }} (fictional hotel, sample rate)</template> · Active days {{ activeDays }} of {{ result.days.length }} · Solver: {{ result.solver_meta.solver_status }}<span v-if="result.solver_meta.solver_status !== 'OPTIMAL'"> (not proven optimal)</span>
              </p>
            </section>

            <BenefitStrip />

            <div class="row g-3 align-items-start" data-testid="tools-row">
              <div class="col-12 col-xl-5"><WhatIfPanel /></div>
              <div class="col-12 col-xl-7"><ItineraryCompare /></div>
            </div>

            <TradeoffExplorer />

            <CostPanel />

            <h2 class="sr-only">Map and day-by-day plan</h2>
            <DaySelector :days="result.days" />
            <div class="row g-3">
              <div class="col-12 col-lg-7"><TripMap :days="result.days" :hotel="hotel" :places-by-id="store.placesById" :selected-day="store.selectedDay" :active-stop="activeStop" @select-stop="selectStop" @hover-stop="activeStop = $event" /></div>
              <div class="col-12 col-lg-5"><DayTimeline :days="result.days" :places-by-id="store.placesById" :fx="store.fx" :hotel-name="hotel?.name ?? 'the hotel'" :locked-ids="lockedIds" :vot-per-hour="store.planPrefs?.value_of_time_per_hour ?? null"
                :cost-days="resp.cost_summary?.days ?? []" :selected-day="store.selectedDay" :active-stop="activeStop" @hover-stop="activeStop = $event">
                <template #actions="{ stop, day }">
                  <StopActions :stop="stop" :day="day" :total-days="result.days.length" :name="store.placesById[stop.attraction_id]?.name ?? stop.attraction_id"
                    :locked="lockedIds.includes(stop.attraction_id)" :disabled="store.busy.replan || solverBusy" @op="queueOp" />
                </template>
              </DayTimeline></div>
            </div>

            <FeasibilityReport :report="resp.feasibility_report" />
            <NotScheduledPanel :missed-ids="result.missed_preferences" :places-by-id="store.placesById" :penalty-jpy="penalty" />
            <CompareDetails />
            <SensitivityPanel />

            <h2 class="mt-4">Change this plan</h2>
            <div v-if="store.restored" class="notice notice-good" role="status" data-testid="restored"><span class="glyph" aria-hidden="true">✓</span><span>The previous plan has been restored. It is the same result the planner gave you earlier; nothing was edited.</span></div>
            <div v-if="store.previous" class="notice notice-info" data-testid="restore-bar">
              <span class="glyph" aria-hidden="true">i</span><span>You are looking at a changed plan. <button type="button" class="btn btn-sm btn-outline-secondary ms-2" @click="restorePrevious" data-testid="restore-previous">Restore previous plan</button></span></div>
            <ErrorPanel v-if="realReplanError" :error="realReplanError" />
            <div v-if="store.lastReplan && store.lastReplan.status !== 'applied'" class="notice notice-info" data-testid="replan-unchanged" role="status">
              <span class="glyph" aria-hidden="true">i</span>
              <div class="w-100"><h3 class="h6 mb-1">Your original plan is unchanged</h3>
                <p class="mb-2">{{ store.lastReplan.summary }}</p>
                <ul v-if="store.lastReplan.conflicts?.length" class="mb-2" data-testid="replan-conflicts"><li v-for="(c, i) in store.lastReplan.conflicts" :key="i">{{ c.message }}</li></ul>
                <FeasibilityReport v-if="store.lastReplan.status === 'rejected_by_validator' && store.lastReplan.feasibility_report" :report="store.lastReplan.feasibility_report" />
                <p class="mb-0 small">The plan above is still the one in force. Your queued changes are kept so you can adjust or undo them.</p></div>
            </div>
            <PendingChanges :queue="store.queue" :places-by-id="store.placesById" :hotels-by-id="store.hotelsById" :hotel-choices="store.hotelIds" :current-hotel="store.chosenHotel"
              :busy="store.busy.replan" :disabled="rateLimited || solverBusy" :error="store.queueError" :budget-now="store.planPrefs?.budget ?? null" @op="queueOp" @remove="unqueue" @clear="clearQueue" @apply="applyClicked" />
            <DiffView v-if="replan && replan.status === 'applied'" :result="replan" :places-by-id="store.placesById" />
            <ExplainBlock v-if="replan && replan.status === 'applied'" title="Explain this change" :explanation="store.explanations.replan" :busy="store.explaining === 'replan'" :disabled="rateLimited || !!store.explaining" :error="store.explainError" @explain="explain('replan')" />
            <ConfirmDialog :open="confirmOpen" title="Remove a must-visit?" confirm-label="Yes, remove it" cancel-label="Keep it in my plan" @cancel="confirmOpen = false" @confirm="confirmed">
              <p class="mb-2">You marked <strong>{{ names(mustRemovals) }}</strong> as a must-visit. Removing it means the new plan will no longer include something you said you required.</p>
              <p class="mb-0 small muted">Nothing is sent unless you confirm. The result will be labelled "Must-visit removed by user".</p>
            </ConfirmDialog>

            <section v-if="result.notes?.length" class="card-soft" data-testid="notes">
              <h2 class="h6">Notes from the planner</h2>
              <ul class="mb-0"><li v-for="n in result.notes" :key="n">{{ n }}</li></ul>
            </section>
          </template>
        </div>
      </div>
    </template>
  </div>
</template>
