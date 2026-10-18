<script setup>
// "Compare with my itinerary": arrange your own days, then see your plan beside the optimiser's for the SAME sights. All placing, validating and scoring is done by the server;
// this component only edits the list of days and displays what came back. Keyboard-accessible move buttons; no drag needed.
import { computed, ref } from 'vue'
import { store, startItinerary, runItineraryCompare, adoptItineraryArm, solverBusy, rateLimited } from '../store.js'
import { addStop, armRows, moveToDay, moveWithin, problems, removeStop } from '../lib/itinerary.js'
import { formatLocalMoney } from '../lib/format.js'
import { cleanHotelText as ct } from '../lib/names.js'

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

function edit(next) { store.itin.days = next; store.itin.result = null }       // any edit makes an old comparison stale: it is cleared, never shown against different days
function toggle() { open.value = !open.value; if (open.value && !store.itin.days) startItinerary() }
</script>
<template>
  <section v-if="store.plan && store.planPrefs" class="card-soft" data-testid="itinerary-compare" aria-labelledby="ic-h">
    <h2 id="ic-h" class="h5 mb-1">Compare with my itinerary</h2>
    <p class="muted small mb-2">Already have a plan in mind? Arrange your own days and see how it compares with the optimiser's plan for the same sights. Estimated travel times from sample data.</p>
    <button type="button" class="btn btn-sm btn-outline-primary" :aria-expanded="open" data-testid="ic-toggle" @click="toggle">{{ open ? 'Hide my itinerary' : 'Arrange my own itinerary' }}</button>

    <div v-if="open && store.itin.days" class="mt-3">
      <div class="row g-3">
        <div v-for="(d, di) in days" :key="di" class="col-12 col-md-6" :data-testid="'ic-day-' + (di + 1)">
          <h3 class="h6">Day {{ di + 1 }}</h3>
          <p v-if="!d.length" class="small muted">Nothing planned.</p>
          <ol class="list-unstyled mb-2">
            <li v-for="(id, i) in d" :key="id" class="d-flex flex-wrap align-items-center gap-1 mb-1" :data-testid="'ic-stop-' + id">
              <span class="me-auto">{{ nameOf(id) }}<span v-if="must.includes(id)" class="pill pill-must ms-1">Must visit</span></span>
              <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="i === 0" :aria-label="`Move ${nameOf(id)} earlier on day ${di + 1}`" @click="edit(moveWithin(days, di, i, -1))">↑</button>
              <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="i === d.length - 1" :aria-label="`Move ${nameOf(id)} later on day ${di + 1}`" @click="edit(moveWithin(days, di, i, 1))">↓</button>
              <select class="form-select form-select-sm w-auto" :aria-label="`Move ${nameOf(id)} to another day`" @change="edit(moveToDay(days, di, i, Number($event.target.value))); $event.target.value = ''">
                <option value="">Move to…</option>
                <option v-for="(_, t) in days" :key="t" v-show="t !== di" :value="t">Day {{ t + 1 }}</option>
              </select>
              <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="must.includes(id)" :aria-label="`Remove ${nameOf(id)}`" :title="must.includes(id) ? 'A must-visit stays in your itinerary' : ''" @click="edit(removeStop(days, di, i, must))">Remove</button>
            </li>
          </ol>
          <div v-if="unused.length" class="d-flex gap-1">
            <select class="form-select form-select-sm" v-model="adding[di]" :aria-label="`Add an attraction to day ${di + 1}`"><option :value="undefined">Add an attraction…</option><option v-for="id in unused" :key="id" :value="id">{{ nameOf(id) }}</option></select>
            <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="!adding[di]" @click="edit(addStop(days, di, adding[di])); adding[di] = undefined">Add</button>
          </div>
        </div>
      </div>
      <ul v-if="errs.length" class="small text-danger mt-2" role="alert"><li v-for="e in errs" :key="e">{{ e }}</li></ul>
      <div class="mt-3 d-flex flex-wrap align-items-center gap-2">
        <button type="button" class="btn btn-primary btn-sm" :disabled="busy || errs.length" data-testid="ic-compare" @click="runItineraryCompare">Compare with the optimiser</button>
        <span v-if="store.itin.busy" class="small muted" role="status">Checking your itinerary and re-running the planner…</span>
      </div>
      <div v-if="store.itin.error" class="notice notice-warn mt-2" role="alert" data-testid="ic-error"><span class="glyph" aria-hidden="true">!</span><span>{{ store.itin.error.message }}</span></div>

      <div v-if="store.itin.result" class="mt-3" data-testid="ic-result">
        <p class="mb-2" data-testid="ic-verdict"><strong>{{ store.itin.result.verdict.text }}</strong></p>
        <div class="table-responsive"><table class="table table-sm align-middle mb-2" data-testid="ic-table">
          <thead><tr><th>Plan</th><th>Works?</th><th>Sights</th><th>Estimated travel</th><th>Admissions + transport (est.)</th><th>Score <span class="muted fw-normal">(not what you pay)</span></th></tr></thead>
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
        <p class="small muted mt-2 mb-0">Choosing an optimised plan keeps your current plan under "Earlier plans" so you can show it again.</p>
      </div>
    </div>
  </section>
</template>
