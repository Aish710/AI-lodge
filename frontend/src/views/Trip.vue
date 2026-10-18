<script setup>
// Screen 2 of 2: the plan. The hotel is switched here, in place; the old plan stays visible (dimmed) until the new one arrives, and a failure never blanks it.
import { costTerms } from '../lib/costTerms.js'
import Icon from '../components/Icon.vue'
import { computed, ref, provide, nextTick } from 'vue'
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
import AiLegend from '../components/AiLegend.vue'
import { checksTally, hotelVerdict, planStatus, sightsCovered } from '../lib/band.js'
import { store, runOptimise, switchHotel, applyAlternative, rateLimited, solverBusy, queueOp, unqueue, clearQueue, applyQueue, restorePrevious, explain, resetAll } from '../store.js'
import { mustVisitRemovals } from '../lib/replan.js'
import { hotelCallout, isInfeasible } from '../lib/rules.js'
import { formatLocalMoney, humanMinutes } from '../lib/format.js'
import { planSummary } from '../lib/planSummary.js'
import EmptyDayHelp from '../components/EmptyDayHelp.vue'
import UndoBar from '../components/UndoBar.vue'
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
const pretty = (t) => costTerms(ct(Object.entries(store.hotelsById).reduce((acc, [id, h]) => acc.split(id).join(h.name), t)))
const lockedIds = computed(() => (store.planPrefs?.locked ?? []).map((l) => l.attraction_id))
const mustRemovals = computed(() => mustVisitRemovals(store.queue, store.planPrefs))
const confirmOpen = ref(false)
const names = (ids) => ids.map((id) => store.placesById[id]?.name ?? id).join(', ')
// The ONLY route to confirm_remove_must_visit = true is this dialog's confirm button.
function applyClicked() { mustRemovals.value.length ? (confirmOpen.value = true) : applyQueue({ confirmed: false }) }
function confirmed() { confirmOpen.value = false; applyQueue({ confirmed: true }) }
async function selectStop({ attractionId }) {
  mobileView.value = 'timeline'
  await nextTick()
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
const section = ref('itinerary')
const sections = [
  { id: 'itinerary', label: 'Itinerary' }, { id: 'costs', label: 'Hotels & Costs' },
  { id: 'ai', label: 'AI Planner' }, { id: 'compare', label: 'Compare & What-if' },
  { id: 'details', label: 'Details & Evidence' },
]
const editor = ref(null)
const mobileView = ref('timeline')
const unknownIds = computed(() => cash.value?.unknown_price_ids ?? t.value?.unknown_cost_items ?? [])
const bookingStops = computed(() => (result.value?.days ?? []).flatMap(d => d.stops ?? []).filter(s => s.uncertainty_flags?.includes('advance_booking_required')).map(s => s.attraction_id))
async function reveal(target) {
  section.value = ({ whatif: 'compare', explorer: 'compare', 'copilot-repair': 'ai', 'pending-tray': 'itinerary' })[target] ?? target
  await nextTick()
}
provide('revealTripSection', reveal)
async function editItinerary() { section.value = 'itinerary'; await nextTick(); editor.value?.showEditor(); document.querySelector('[data-testid="itinerary-compare"]')?.scrollIntoView({ block: 'start' }) }
function sectionKey(e, i) {
  const n = sections.length
  const to = e.key === 'ArrowRight' ? (i + 1) % n : e.key === 'ArrowLeft' ? (i + n - 1) % n : e.key === 'Home' ? 0 : e.key === 'End' ? n - 1 : null
  if (to === null) return
  e.preventDefault(); section.value = sections[to].id
  document.getElementById(`trip-tab-${section.value}`)?.focus()
}
</script>

<template>
  <div class="stack trip-workspace">
    <header class="trip-heading">
      <div><p class="eyebrow">Your city, your pace</p><h1>{{ store.city?.display_name ?? 'Your' }} trip</h1>
        <p class="muted mb-0">{{ store.planPrefs?.days ?? store.form.days }} days<template v-if="hotel"> · {{ hotel.name }} · Demo hotel</template></p>
      </div>
      <div class="d-flex flex-wrap gap-2">
        <button class="btn btn-outline-primary btn-sm" @click="router.push('/')" data-testid="edit-trip">Edit trip</button>
        <button class="btn btn-outline-secondary btn-sm" :disabled="planning || solverBusy || rateLimited || !store.chosenHotel" @click="runOptimise()">Recalculate</button>
        <button class="btn btn-link btn-sm" @click="startOver" data-testid="start-over">New adventure</button>
      </div>
    </header>
    <UndoBar v-if="resp" />
    <div v-if="!resp && !planning" class="card-soft" data-testid="itinerary-empty">
      <p>No plan yet. Choose your sights, then plan your trip.</p>
      <button class="btn btn-primary" @click="router.push('/')" data-testid="go-plan">Go to Plan</button>
    </div>
    <BusyNotice :error="busyError" @retry="retry" />
    <ErrorPanel v-if="realPlanError" :error="realPlanError" retryable @retry="retry" />
    <PlanProgress switching />
    <template v-if="resp">
      <template v-if="infeasible">
            <HotelSwitch />   <!-- a blocked hotel must still be switchable: the other hotels may be feasible -->
            <StatusChip v-bind="status" />
            <div data-testid="copilot-repair" tabindex="-1"><ConflictPanel :result="result" :prefs="store.planPrefs" :places-by-id="store.placesById" :busy="store.busy.optimise" :disabled="rateLimited || solverBusy" @apply="applyAlternative">
              <template #assistant><RepairAssistant /></template>
            </ConflictPanel></div>
            <FeasibilityReport :report="resp.feasibility_report" />
        <TripCopilot />
      </template>
      <template v-else>
        <section class="trip-overview" aria-label="Plan summary" data-testid="totals">
          <div class="overview-status"><StatusChip v-bind="status" /><span class="small muted">Checked against sample data</span></div>
          <dl class="overview-metrics">
            <div><dt>Modelled cash incl. rooms</dt><dd data-testid="kpi-total">{{ cash?.cash_total_with_rooms == null ? 'Unavailable' : money(cash.cash_total_with_rooms) }}</dd><p class="small muted mb-0" data-testid="kpi-total-parts">Sights & transport {{ money(t.total_jpy) }}<template v-if="cash"> + rooms {{ money(cash.rooms) }} · {{ cash.nights }} nights</template><template v-else> · Room-inclusive summary unavailable; check the API version.</template></p></div>
            <div><dt>Estimated travel</dt><dd data-testid="kpi-travel">{{ humanMinutes(t.travel_minutes) }}</dd></div>
            <div><dt>Attractions scheduled</dt><dd data-testid="kpi-sights">{{ cover.scheduled }} of {{ cover.wanted }}</dd></div>
            <div><dt>Active days</dt><dd data-testid="kpi-active-days">{{ activeDays }} of {{ result.days.length }}</dd></div>
          </dl>
          <p v-if="unknownIds.length" class="cost-warning" role="status" data-testid="overview-unknown">{{ unknownIds.length }} admission price(s) unknown and excluded: {{ names(unknownIds) }}. They are not free.</p>
          <p v-if="bookingStops.length" class="small" role="status">Booking required: {{ names(bookingStops) }}. Check availability before you travel.</p>
          <p v-if="cash && store.planPrefs?.budget != null && cash.cash_total > store.planPrefs.budget" class="cost-warning" role="status">Sights and transport exceed your budget target by {{ money(cash.cash_total - store.planPrefs.budget) }}. Review Hotels & Costs.</p>
          <p class="small muted mb-0">Fictional hotel rates and estimated transport. Food excluded. Your budget applies to sights and transport only.</p>
        </section>
            <div v-if="resp.feasibility_report?.verification === 'conditional'" class="notice notice-warn" role="status" data-testid="conditional-banner">
              <span class="glyph" aria-hidden="true">!</span>
              <span><strong>Provisional plan. Opening hours unverified.</strong> This plan is feasible only if {{ (resp.feasibility_report.conditional_stop_ids ?? []).map((id) => store.placesById[id]?.name ?? id).join(', ') }} {{ (resp.feasibility_report.conditional_stop_ids ?? []).length === 1 ? 'is' : 'are' }} open at the scheduled time; the sample data does not say. Check the opening hours before you travel. It is not a verified itinerary.</span>
            </div>
            <div class="notice notice-warn" v-if="resp.approximate || comp?.approximate || comp?.partial" role="status" data-testid="approximate">
              <span class="glyph" aria-hidden="true">!</span><span><strong>Approximate.</strong> {{ resp.approximate ? resp.approximate_note : 'The comparison was not fully proven optimal, so the lowest possible generalised cost is not proven.' }}</span>
            </div>

        <div v-if="resp.feasibility_report?.overall === 'fail'" class="notice notice-error" role="alert"><strong>Independent validation failed. Check Details & Evidence before using this plan.</strong></div>
        <div v-if="store.queue.length" class="notice notice-info queued-notice" role="status"><span>{{ store.queue.length }} pending change(s). Your accepted plan is unchanged.</span><button class="btn btn-sm btn-outline-primary" @click="reveal('itinerary')">Review changes</button></div>
        <div class="trip-tabs" role="tablist" aria-label="Your trip sections">
          <button v-for="(item, i) in sections" :key="item.id" :id="`trip-tab-${item.id}`" role="tab" type="button" :aria-selected="section === item.id" :aria-controls="`trip-panel-${item.id}`" :tabindex="section === item.id ? 0 : -1" :data-testid="`trip-tab-${item.id}`" @click="section = item.id" @keydown="sectionKey($event, i)">{{ item.label }}</button>
        </div>
        <div :class="{ dimmed: planning }" :aria-busy="planning" data-testid="trip-body">
          <section id="trip-panel-itinerary" role="tabpanel" aria-labelledby="trip-tab-itinerary" v-show="section === 'itinerary'" class="stack" tabindex="0">
            <div class="section-heading"><div><h2>Your daily itinerary</h2><p class="muted mb-0">Explore a day. Select a pin to find its activity.</p></div>
              <div class="d-flex flex-wrap gap-2"><button class="btn btn-outline-primary" data-testid="edit-itinerary" @click="editItinerary">Edit itinerary</button><button class="btn btn-primary" @click="section = 'ai'" data-testid="ask-ai-entry">Ask Fitinerary AI</button></div>
            </div>
            <div class="mobile-map-toggle" role="group" aria-label="Itinerary view"><button type="button" :aria-pressed="mobileView === 'timeline'" @click="mobileView = 'timeline'">Timeline</button><button type="button" :aria-pressed="mobileView === 'map'" @click="mobileView = 'map'">Map</button></div>
            <h2 class="sr-only">Map and day-by-day plan</h2>
            <DaySelector :days="result.days" />
            <div id="day-content" role="tabpanel" :aria-labelledby="`daychip-${store.selectedDay}`" tabindex="0" class="itinerary-layout" :class="`mobile-${mobileView}`">
              <div class="itinerary-map"><TripMap :days="result.days" :hotel="hotel" :places-by-id="store.placesById" :selected-day="store.selectedDay" :active-stop="activeStop" @select-stop="selectStop" @hover-stop="activeStop = $event" /></div>
              <div class="itinerary-timeline"><DayTimeline :days="result.days" :places-by-id="store.placesById" :fx="store.fx" :hotel-name="hotel?.name ?? 'the hotel'" :locked-ids="lockedIds" :vot-per-hour="store.planPrefs?.value_of_time_per_hour ?? null"
                :cost-days="resp.cost_summary?.days ?? []" :selected-day="store.selectedDay" :active-stop="activeStop" @hover-stop="activeStop = $event">
                <template #actions="{ stop, day }">
                  <StopActions :stop="stop" :day="day" :total-days="result.days.length" :name="store.placesById[stop.attraction_id]?.name ?? stop.attraction_id"
                    :locked="lockedIds.includes(stop.attraction_id)" :disabled="store.busy.replan || solverBusy" @op="queueOp" />
                </template>
              </DayTimeline></div>
            </div>

            <EmptyDayHelp />
            <ItineraryCompare ref="editor" />
            <NotScheduledPanel :missed-ids="result.missed_preferences" :places-by-id="store.placesById" :penalty-jpy="penalty" />
            <h2 class="h5" v-if="store.queue.length || replan || store.previous">Changes to your plan</h2>
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

          </section>
          <section id="trip-panel-costs" role="tabpanel" aria-labelledby="trip-tab-costs" v-show="section === 'costs'" class="stack" tabindex="0">
            <h2>Hotels & Costs</h2>
            <HotelSwitch />
            <section v-if="verdict" class="window verdict-window" :class="`verdict-${verdict.kind}`" data-title="verdict.exe" data-tone="cyan" data-testid="verdict" aria-live="polite">
              <Icon :name="verdict.kind === 'good' ? 'check' : 'warn'" :size="34" class="verdict-icon" />
              <div><div class="verdict">{{ verdict.headline }} <AiMark kind="calc" /></div>
              <div class="verdict-detail">{{ verdict.detail }}</div></div>
              <HowMade class="mt-2" :explained="store.explanations.compare?.source ?? null" />
            </section>
            <div v-if="callout.kind === 'differs'" class="notice notice-good" role="status" data-testid="callout-differs"><span class="glyph" aria-hidden="true">✓</span><span><strong>{{ callout.text }}</strong></span></div>
            <details v-if="comp?.insight" class="small" data-testid="insight-details"><summary>Why?</summary><p class="mb-0 mt-1" data-testid="insight">{{ pretty(comp.insight) }}</p></details>
            <CostPanel />
            <CompareDetails />
            <SensitivityPanel />
          </section>
          <section id="trip-panel-ai" role="tabpanel" aria-labelledby="trip-tab-ai" v-show="section === 'ai'" class="stack" tabindex="0">
            <TripCopilot />
            <details class="card-soft" data-testid="more-ai-edit" :open="store.moreAiOpen" @toggle="store.moreAiOpen = $event.target.open">
              <summary class="fw-semibold">More ways to ask for a change</summary>
              <p class="small muted mt-2">These do the same kind of thing as the box above, with more detail. Everything is previewed and checked before you apply it.</p>
              <div data-testid="copilot-repair" tabindex="-1"><RepairAssistant /></div>
              <ProposedOperations class="mt-3" />
            </details>

            <ExplainBlock :summary="summary" :days="result.days" :explanation="store.explanations.optimise" :busy="store.explaining === 'optimise'" :disabled="rateLimited || !!store.explaining" :error="store.explainError" @explain="explain('optimise')" />
          </section>
          <section id="trip-panel-compare" role="tabpanel" aria-labelledby="trip-tab-compare" v-show="section === 'compare'" class="stack" tabindex="0">
            <h2>Compare & What-if</h2>
            <p class="muted">Preview another scenario or explore trade-offs. Nothing replaces your trip until you choose Apply.</p>
            <WhatIfPanel /><TradeoffExplorer />
          </section>
          <section id="trip-panel-details" role="tabpanel" aria-labelledby="trip-tab-details" v-show="section === 'details'" class="stack" tabindex="0">
            <h2>Details & Evidence</h2><SettingsSummaryStrip /><AiLegend />
            <FeasibilityReport :report="resp.feasibility_report" compact />
            <p class="small" data-testid="kpi-checks">{{ tally.passed }} of {{ tally.total }} checks passed · Solver: {{ result.solver_meta?.solver_status }}<span v-if="result.solver_meta?.solver_status !== 'OPTIMAL'"> (not proven optimal)</span></p>
            <GettingAround /><BenefitStrip />
            <section v-if="result.notes?.length" class="card-soft" data-testid="notes">
              <h2 class="h6">Notes from the planner</h2>
              <ul class="mb-0"><li v-for="n in result.notes" :key="n">{{ n }}</li></ul>
            </section>
          </section>
        </div>
      </template>
    </template>
  </div>
</template>
