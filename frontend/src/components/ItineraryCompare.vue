<script setup>
// "Compare with my itinerary": build your own days by DRAGGING sights between days (or with the keyboard-accessible buttons), watch live feedback from the independent validator,
// then compare with the optimiser's plan for the same sights. All placing, validating and scoring is done by the server; this component edits the list of days and shows what came back.
// Drag-and-drop uses the browser's native events (mouse and pen); touch screens use the arrow and "Move to" controls, which do the same thing.
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { store, startItinerary, runItineraryCompare, adoptItineraryArm, checkDraft, solverBusy, rateLimited } from '../store.js'
import { addStop, armRows, moveAnnouncement, moveStop, moveToDay, moveWithin, problems, removeStop } from '../lib/itinerary.js'
import { formatLocalMoney } from '../lib/format.js'
import { cleanHotelText as ct } from '../lib/names.js'

// ?builder=classic switches off drag-and-drop and live feedback (arrow buttons only), so a usability study can compare the two workflows with the same planner behind them
const classic = computed(() => store.classicBuilder)
const open = ref(false)
const money = (v) => (v === null || v === undefined ? '—' : formatLocalMoney(v, store.city?.currency_code ?? 'JPY'))
const mins = (m) => (m === null || m === undefined ? '—' : m >= 60 ? `${Math.floor(m / 60)} h ${Math.round(m % 60)} min` : `${Math.round(m)} min`)
const nameOf = (id) => ct(store.placesById[id]?.name ?? id)
const must = computed(() => store.planPrefs?.must_visit ?? [])
const days = computed(() => store.itin.days ?? [])
const errs = computed(() => problems(days.value, must.value))
const busy = computed(() => store.itin.busy || solverBusy.value || rateLimited.value)
const rows = computed(() => armRows(store.itin.result))
const unused = computed(() => Object.keys(store.placesById).filter((id) => !days.value.flat().includes(id) && store.wishlist[id] !== 'skip'))
const adding = ref({})
const live = computed(() => store.itin.live)
const liveStop = (id) => live.value?.stops?.find((s) => s.id === id)
const announce = ref('')

let timer = null
function schedule() { if (classic.value) return; clearTimeout(timer); timer = setTimeout(() => checkDraft(), 350) }       // debounced: no request per pixel of dragging
onBeforeUnmount(() => clearTimeout(timer))
watch(() => store.itin.days, () => { if (open.value) schedule() }, { deep: true })

function edit(next, id = null) {
  if (next === store.itin.days) return
  store.itin.days = next; store.itin.result = null
  if (id) announce.value = moveAnnouncement(nameOf(id), next, id)
}
function toggle() { open.value = !open.value; if (open.value && !store.itin.days) startItinerary(); if (open.value) schedule() }

// ---- drag and drop ----
const drag = ref(null)       // {day, index, id}
const over = ref(null)       // {day, index}   index = the slot the item would take
function onStart(di, i, e) { drag.value = { day: di, index: i, id: days.value[di][i] }; e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', days.value[di][i]) }
function onEnd() { drag.value = null; over.value = null }
function slot(e, di, i) { const r = e.currentTarget.getBoundingClientRect(); return { day: di, index: e.clientY - r.top > r.height / 2 ? i + 1 : i } }
// While a stop is dragged, scroll the page when the pointer nears the top or bottom edge, so a day that is below (or above) the visible area can still be reached.
function autoscroll(e) { const m = 70, y = e.clientY, h = window.innerHeight; if (y > h - m) window.scrollBy(0, Math.ceil((y - (h - m)) / 3)); else if (y < m) window.scrollBy(0, -Math.ceil((m - y) / 3)) }
function onOverItem(e, di, i) { if (!drag.value) return; autoscroll(e); e.preventDefault(); e.stopPropagation(); over.value = slot(e, di, i); e.dataTransfer.dropEffect = 'move' }
function onOverDay(e, di) { if (!drag.value) return; autoscroll(e); e.preventDefault(); if (!over.value || over.value.day !== di) over.value = { day: di, index: days.value[di].length } }
function onDrop(e, di) {
  if (!drag.value) return
  e.preventDefault()
  const to = over.value && over.value.day === di ? over.value : { day: di, index: days.value[di].length }
  const id = drag.value.id
  const next = moveStop(days.value, { day: drag.value.day, index: drag.value.index }, to)
  if (next === days.value && drag.value.day !== to.day) announce.value = `Day ${to.day + 1} already has the maximum number of stops.`
  edit(next, id); onEnd()
}
async function keyMove(next, id) { edit(next, id); await nextTick(); document.querySelector(`[data-testid="ic-stop-${id}"] [data-focus]`)?.focus() }
</script>
<template>
  <section v-if="store.plan && store.planPrefs" class="card-soft" data-testid="itinerary-compare" aria-labelledby="ic-h">
    <h2 id="ic-h" class="h5 mb-1">Compare with my itinerary</h2>
    <p class="muted small mb-2">Already have a plan in mind? Drag sights between days (or use the arrows), see at once whether your draft works, then compare it with the optimiser's plan for the same sights. Estimated travel times from sample data.</p>
    <button type="button" class="btn btn-sm btn-outline-primary" :aria-expanded="open" data-testid="ic-toggle" @click="toggle">{{ open ? 'Hide my itinerary' : 'Arrange my own itinerary' }}</button>

    <div v-if="open && store.itin.days" class="mt-3">
      <p class="visually-hidden" role="status" aria-live="polite" data-testid="ic-announce">{{ announce }}</p>
      <div v-if="!classic" class="small mb-2" :class="live?.feasible ? 'text-success' : ''" aria-live="polite" data-testid="ic-live">
        <template v-if="store.itin.liveBusy && !live">Checking your draft…</template>
        <template v-else-if="live?.error"><strong class="text-danger">Your draft could not be validated.</strong> {{ live.error }} Nothing is claimed about it until it is checked.
          <button type="button" class="btn btn-sm btn-outline-secondary ms-1" data-testid="ic-recheck" @click="checkDraft">Check again</button></template>
        <template v-else-if="live">
          <strong>{{ live.feasible ? 'Your draft works' : 'Your draft has a problem' }}</strong>
          <template v-if="live.feasible"> · {{ live.active_days }} active day{{ live.active_days === 1 ? '' : 's' }} · estimated spending incl. rooms {{ money(live.cash?.cash_total_with_rooms) }} · estimated travel {{ mins(live.cash?.travel_minutes) }}<span v-if="live.verification === 'conditional'"> · provisional: some opening hours are unverified</span></template>
          <ul v-else class="mb-0 ps-3"><li v-for="c in [...live.conflicts, ...live.failed_checks.map((x) => 'Check failed: ' + x)].slice(0, 4)" :key="c">{{ c }}</li></ul>
        </template>
        <span v-if="store.itin.liveBusy && live" class="muted"> (updating…)</span>
      </div>
      <div class="row g-3">
        <div v-for="(d, di) in days" :key="di" class="col-12 col-md-6 col-xl-4" :data-testid="'ic-day-' + (di + 1)">
          <div class="border rounded p-2 h-100" :class="{ 'ic-over': over && over.day === di && drag }" @dragover="!classic && onOverDay($event, di)" @drop="!classic && onDrop($event, di)" @dragleave.self="over = null">
            <h3 class="h6">Day {{ di + 1 }} <span class="small muted fw-normal">{{ d.length }} stop{{ d.length === 1 ? '' : 's' }}</span></h3>
            <p v-if="!d.length" class="small muted mb-1" data-testid="ic-empty-day">Nothing planned. Drop a sight here.</p>
            <ol class="list-unstyled mb-2" :aria-label="'Day ' + (di + 1) + ' stops'">
              <li v-for="(id, i) in d" :key="id" class="ic-stop mb-1" :class="{ 'ic-dragging': drag && drag.id === id, 'ic-before': over && over.day === di && over.index === i && drag && drag.id !== id, 'ic-problem': liveStop(id)?.problem }"
                :data-testid="'ic-stop-' + id" :draggable="!classic" @dragstart="!classic && onStart(di, i, $event)" @dragend="onEnd" @dragover="!classic && onOverItem($event, di, i)" @drop="!classic && onDrop($event, di)">
                <div class="d-flex flex-wrap align-items-center gap-1">
                  <span v-if="!classic" class="ic-handle" aria-hidden="true" title="Drag to move">⠿</span>
                  <span class="me-auto">{{ nameOf(id) }}<span v-if="must.includes(id)" class="pill pill-must ms-1">Must visit</span>
                    <span v-if="liveStop(id)?.start" class="small muted d-block" :data-testid="'ic-time-' + id">{{ liveStop(id).start }}–{{ liveStop(id).end }}</span></span>
                  <button type="button" data-focus class="btn btn-sm btn-outline-secondary" :disabled="i === 0" :aria-label="`Move ${nameOf(id)} earlier on day ${di + 1}`" @click="keyMove(moveWithin(days, di, i, -1), id)">↑</button>
                  <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="i === d.length - 1" :aria-label="`Move ${nameOf(id)} later on day ${di + 1}`" @click="keyMove(moveWithin(days, di, i, 1), id)">↓</button>
                  <select class="form-select form-select-sm w-auto" :aria-label="`Move ${nameOf(id)} to another day`" @change="keyMove(moveToDay(days, di, i, Number($event.target.value)), id); $event.target.value = ''">
                    <option value="">Move to…</option>
                    <option v-for="(_, t) in days" :key="t" v-show="t !== di" :value="t">Day {{ t + 1 }}</option>
                  </select>
                  <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="must.includes(id)" :aria-label="`Remove ${nameOf(id)}`" :title="must.includes(id) ? 'A must-visit stays in your itinerary' : ''" @click="edit(removeStop(days, di, i, must))">Remove</button>
                </div>
                <div v-if="liveStop(id)?.problem" class="small text-danger" role="note" :data-testid="'ic-problem-' + id">{{ liveStop(id).problem }}</div>
              </li>
              <li v-if="over && over.day === di && drag && over.index >= d.length" class="ic-end" aria-hidden="true"></li>
            </ol>
            <div v-if="unused.length" class="d-flex gap-1">
              <select class="form-select form-select-sm" v-model="adding[di]" :aria-label="`Add an attraction to day ${di + 1}`"><option :value="undefined">Add an attraction…</option><option v-for="id in unused" :key="id" :value="id">{{ nameOf(id) }}</option></select>
              <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="!adding[di]" @click="edit(addStop(days, di, adding[di])); adding[di] = undefined">Add</button>
            </div>
          </div>
        </div>
      </div>
      <p class="small muted mt-2 mb-0">Touch screen? Use the arrows and "Move to…": they do the same as dragging.</p>
      <ul v-if="errs.length" class="small text-danger mt-2" role="alert"><li v-for="e in errs" :key="e">{{ e }}</li></ul>
      <div class="mt-3 d-flex flex-wrap align-items-center gap-2">
        <button type="button" class="btn btn-primary btn-sm" :disabled="busy || errs.length" data-testid="ic-compare" @click="runItineraryCompare">Compare with the optimiser</button>
        <span v-if="store.itin.busy" class="small muted" role="status">Checking your itinerary and re-running the planner…</span>
      </div>
      <div v-if="store.itin.error" class="notice notice-warn mt-2" role="alert" data-testid="ic-error"><span class="glyph" aria-hidden="true">!</span><span>{{ store.itin.error.message }}</span></div>

      <div v-if="store.itin.result" class="mt-3" data-testid="ic-result">
        <p class="mb-2" data-testid="ic-verdict"><strong>{{ store.itin.result.verdict.text }}</strong></p>
        <div class="table-responsive"><table class="table table-sm align-middle mb-2" data-testid="ic-table">
          <thead><tr><th>Plan</th><th>Works?</th><th>Sights</th><th>Estimated travel</th><th>Admissions + transport (est.)</th><th>Generalised cost <span class="muted fw-normal">(not what you pay)</span></th></tr></thead>
          <tbody><tr v-for="r in rows" :key="r.key" :data-testid="'ic-row-' + r.key">
            <th scope="row">{{ r.label }}</th>
            <td>{{ r.feasible ? 'Yes' : 'No' }}<span v-if="!r.feasible" class="small d-block">{{ r.why }}</span></td>
            <td>{{ r.feasible ? r.sights : '—' }}<span v-if="r.omitted.length" class="small muted d-block">{{ r.omitted.length }} optional left out</span></td>
            <td>{{ mins(r.minutes) }}</td><td>{{ money(r.spend) }}</td><td>{{ money(r.score) }}</td></tr></tbody>
        </table></div>
        <p v-if="store.itin.result.full_plan.different_sights" class="small muted" data-testid="ic-different">The full plan visits different sights from yours (it leaves out {{ store.itin.result.full_plan.sights_left_out.map(nameOf).join(', ') }}), so its travel time is not a like-for-like saving.</p>
        <div class="d-flex flex-wrap gap-2">
          <button type="button" class="btn btn-sm btn-primary" :disabled="busy || !store.itin.result.arms[1].feasible" data-testid="ic-use-same" @click="adoptItineraryArm('same')">Use the optimised plan (same sights)</button>
          <button type="button" class="btn btn-sm btn-outline-primary" :disabled="busy || !store.itin.result.arms[2].feasible" data-testid="ic-use-full" @click="adoptItineraryArm('full')">Use the full optimised plan</button>
          <button type="button" class="btn btn-sm btn-outline-secondary" data-testid="ic-keep" @click="store.itin.result = null">Keep what I have</button>
        </div>
        <p class="small muted mt-2 mb-0">Choosing an optimised plan keeps your current plan under "Earlier plans" so you can show it again. Your draft is never applied as your plan: only a plan the optimiser and validator produced can be.</p>
      </div>
    </div>
  </section>
</template>
<style scoped>
.ic-stop { border: 1px solid var(--bs-border-color, #dee2e6); border-radius: 6px; padding: 6px 8px; background: #fff; cursor: grab; }
.ic-handle { cursor: grab; color: #6c757d; user-select: none; padding: 0 4px; }
.ic-dragging { opacity: .45; }
.ic-before { box-shadow: 0 -3px 0 0 #b3261e; }
.ic-over { outline: 2px dashed #b3261e; outline-offset: 2px; }
.ic-end { height: 4px; background: #b3261e; border-radius: 2px; }
.ic-problem { border-color: #b3261e; }
</style>
