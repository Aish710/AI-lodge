<script setup>
// What if?: change a few settings on a COPY of the current plan, see the real optimiser's answer beside the plan you have, then Apply, Save or Discard.
// The plan you are looking at is never changed by a preview. All numbers come from the server; this component only subtracts two of them.
import { computed, ref, watch } from 'vue'
import { store, openWhatIf, runWhatIf, discardWhatIf, applyWhatIf, saveWhatIf, solverBusy, rateLimited } from '../store.js'
import { diffPlans, validationOf, WHATIF_PACES } from '../lib/whatif.js'
import { formatLocalMoney } from '../lib/format.js'
import { cleanHotelText as ct } from '../lib/names.js'

const open = ref(false)
watch(() => store.whatif.draft, (v) => { if (v) open.value = true })   // opened from elsewhere, for example a copilot proposal
const w = computed(() => store.whatif)
const d = computed(() => store.whatif.draft)
const money = (v) => (v === null || v === undefined ? '—' : formatLocalMoney(v, store.city?.currency_code ?? 'JPY'))
const mins = (m) => (m === null || m === undefined ? '—' : `${Math.round(m)} min`)
const signed = (v, f) => (v === null ? '—' : v === 0 ? 'no change' : `${v > 0 ? '+' : '−'}${f(Math.abs(v))}`)
const name = (id) => ct(store.placesById[id]?.name ?? id)
const hotels = computed(() => Object.values(store.hotelsById ?? {}))
const stops = computed(() => (store.plan?.result?.days ?? []).flatMap((x) => x.stops.map((s) => s.attraction_id)))
const others = computed(() => Object.keys(store.placesById).filter((id) => !stops.value.includes(id) && store.wishlist[id] !== 'skip'))
const feasible = computed(() => w.value.result?.result?.status === 'feasible')
const diff = computed(() => (feasible.value ? diffPlans(store.plan, w.value.result) : null))
const validation = computed(() => validationOf(w.value.result))
const busy = computed(() => solverBusy.value || rateLimited.value)
function toggle() { open.value = !open.value; if (open.value && !store.whatif.draft) openWhatIf(); if (!open.value) discardWhatIf() }
function pick(list, id, on) { const s = new Set(list); on ? s.add(id) : s.delete(id); return [...s] }
</script>
<template>
  <section v-if="store.plan && store.planPrefs" class="card-soft" data-testid="whatif" tabindex="-1" aria-labelledby="wi-h">
    <h2 id="wi-h" class="h5 mb-1">What if?</h2>
    <p class="muted small mb-2">Try a change on a copy of this plan. Nothing changes here until you press Apply.</p>
    <button type="button" class="btn btn-sm btn-outline-primary" :aria-expanded="open" data-testid="wi-toggle" @click="toggle">{{ open ? 'Close' : 'Try a what-if' }}</button>

    <div v-if="open && d" class="mt-3">
      <div class="row g-2">
        <div class="col-6 col-md-3"><label class="form-label small" for="wi-days">Days</label><input id="wi-days" class="form-control form-control-sm" type="number" min="1" max="7" v-model.number="d.days" data-testid="wi-days" /></div>
        <div class="col-6 col-md-3"><label class="form-label small" for="wi-end">Day ends</label><input id="wi-end" class="form-control form-control-sm" type="time" v-model="d.dayEnd" data-testid="wi-end" /></div>
        <div class="col-6 col-md-3"><label class="form-label small" for="wi-pace">Pace</label><select id="wi-pace" class="form-select form-select-sm" v-model="d.pace"><option v-for="p in WHATIF_PACES" :key="p" :value="p">{{ p }}</option></select></div>
        <div class="col-6 col-md-3"><label class="form-label small" for="wi-budget">Budget (blank = none)</label><input id="wi-budget" class="form-control form-control-sm" type="number" min="0" v-model="d.budget" data-testid="wi-budget" /></div>
        <div class="col-6 col-md-3"><div class="form-check mt-4"><input id="wi-strict" class="form-check-input" type="checkbox" v-model="d.strict" /><label class="form-check-label small" for="wi-strict">Strict budget</label></div></div>
        <div class="col-6 col-md-3"><label class="form-label small" for="wi-act">Max activities a day</label><input id="wi-act" class="form-control form-control-sm" type="number" min="1" max="8" v-model="d.maxActivities" data-testid="wi-act" /></div>
        <div class="col-6 col-md-3"><label class="form-label small" for="wi-trv">Max est. travel a day (min)</label><input id="wi-trv" class="form-control form-control-sm" type="number" min="20" max="720" v-model="d.maxDailyTravel" data-testid="wi-trv" /></div>
        <div class="col-6 col-md-3"><label class="form-label small" for="wi-minact">At least this many active days</label><input id="wi-minact" class="form-control form-control-sm" type="number" min="1" :max="d.days" v-model="d.minActive" data-testid="wi-minact" /></div>
        <div class="col-6 col-md-3"><label class="form-label small" for="wi-vot">Value of an hour</label><input id="wi-vot" class="form-control form-control-sm" type="number" min="0" v-model.number="d.vot" data-testid="wi-vot" /></div>
        <div class="col-12 col-md-6"><label class="form-label small" for="wi-hotel">Hotel</label><select id="wi-hotel" class="form-select form-select-sm" v-model="d.hotel"><option v-for="h in hotels" :key="h.id" :value="h.id">{{ ct(h.name) }}</option></select></div>
      </div>
      <div class="row g-2 mt-1">
        <div class="col-12 col-md-6"><div class="small fw-semibold">Leave out</div>
          <div v-for="id in stops" :key="id" class="form-check"><input :id="'wi-ex-' + id" class="form-check-input" type="checkbox" :checked="d.exclude.includes(id)" @change="d.exclude = pick(d.exclude, id, $event.target.checked)" :data-testid="'wi-ex-' + id" /><label class="form-check-label small" :for="'wi-ex-' + id">{{ name(id) }}<span v-if="store.planPrefs.must_visit.includes(id)" class="pill pill-must ms-1">Must visit</span></label></div></div>
        <div v-if="others.length" class="col-12 col-md-6"><div class="small fw-semibold">Add as must-visit</div>
          <div v-for="id in others" :key="id" class="form-check"><input :id="'wi-add-' + id" class="form-check-input" type="checkbox" :checked="d.addMust.includes(id)" @change="d.addMust = pick(d.addMust, id, $event.target.checked)" /><label class="form-check-label small" :for="'wi-add-' + id">{{ name(id) }}</label></div></div>
      </div>
      <div class="mt-3 d-flex flex-wrap align-items-center gap-2">
        <button type="button" class="btn btn-primary btn-sm" :disabled="busy" data-testid="wi-run" @click="runWhatIf">Preview this what-if</button>
        <button type="button" class="btn btn-outline-secondary btn-sm" data-testid="wi-discard" @click="discardWhatIf(); open = false">Discard</button>
        <span v-if="w.busy" class="small muted" role="status">Re-running the planner on a copy…</span>
      </div>
      <div v-if="w.error" class="notice notice-warn mt-2" role="alert" data-testid="wi-error"><span class="glyph" aria-hidden="true">!</span><span>{{ w.error.message }}</span></div>

      <div v-if="w.result && !feasible" class="notice notice-info mt-2" data-testid="wi-infeasible">
        <span class="glyph" aria-hidden="true">i</span><span><strong>This what-if has no feasible plan.</strong> Your current plan is unchanged. <span v-for="c in w.result.result.conflicts.slice(0, 3)" :key="c.code + c.message" class="d-block small">{{ c.message }}</span></span>
      </div>

      <div v-if="feasible && diff" class="mt-3" data-testid="wi-result">
        <p class="mb-2" role="status" :class="{ 'text-danger': validation.kind === 'bad' || validation.kind === 'unknown' }" data-testid="wi-validation"><strong>Validation: {{ validation.text }}</strong> <span class="small muted">Estimated travel and the demo hotel's sample prices remain assumptions.</span></p>
        <p v-if="diff.empty" class="small text-danger" data-testid="wi-empty">This what-if schedules no sights at all. It is "feasible" only because nothing is asked of it.</p>
        <p class="small muted mb-1">What changes: {{ w.scenario.changes.join(', ') }}.</p>
        <div class="table-responsive"><table class="table table-sm align-middle mb-2" data-testid="wi-table">
          <thead><tr><th></th><th>Current plan</th><th>What-if</th><th>Difference</th></tr></thead>
          <tbody>
            <tr><th scope="row">Hotel</th><td>{{ ct(store.hotelsById[store.chosenHotel]?.name ?? store.chosenHotel) }}</td><td>{{ ct(store.hotelsById[w.scenario.hotel]?.name ?? w.scenario.hotel) }}</td><td>{{ w.scenario.hotel === store.chosenHotel ? 'same' : 'different' }}</td></tr>
            <tr><th scope="row">Spending incl. rooms (est.)</th><td>{{ money(store.plan.cost_summary?.trip.cash_total_with_rooms) }}</td><td>{{ money(w.result.cost_summary?.trip.cash_total_with_rooms) }}</td><td data-testid="wi-money">{{ diff.comparable ? signed(diff.money, money) : 'not comparable' }}</td></tr>
            <tr><th scope="row">Estimated travel</th><td>{{ mins(store.plan.cost_summary?.trip.travel_minutes) }}</td><td>{{ mins(w.result.cost_summary?.trip.travel_minutes) }}</td><td data-testid="wi-minutes">{{ diff.comparable ? signed(diff.minutes, mins) : 'not comparable' }}</td></tr>
            <tr><th scope="row">Sights</th><td>{{ stops.length }}</td><td>{{ stops.length + diff.sights }}</td><td>{{ signed(diff.sights, String) }}</td></tr>
          </tbody></table></div>
        <ul class="small mb-2">
          <li v-if="diff.added.length">Added: {{ diff.added.map(name).join(', ') }}</li>
          <li v-if="diff.removed.length">Removed: {{ diff.removed.map(name).join(', ') }}</li>
          <li v-if="diff.moved.length">Moved to another day: {{ diff.moved.map(name).join(', ') }}</li>
          <li v-if="!diff.added.length && !diff.removed.length && !diff.moved.length">The same sights on the same days.</li>
        </ul>
        <p class="small muted" data-testid="wi-fixed">The preview preserves settings not listed above. Check added and removed sights before comparing spending; different coverage is not like-for-like savings.</p>
        <p v-if="diff.lowerBecauseLess" class="small" data-testid="wi-lower-because-less"><strong>Lower modelled spending here comes from visiting fewer sights, not from planning the same trip more cheaply.</strong> A like-for-like saving needs the same sights.</p>
        <p v-if="diff.note" class="small muted" data-testid="wi-note">{{ diff.note }}</p>
        <div class="d-flex flex-wrap gap-2">
          <button type="button" class="btn btn-sm btn-primary" :disabled="busy || !validation.applicable" data-testid="wi-apply" @click="applyWhatIf(); open = false">Apply this what-if</button>
          <button type="button" class="btn btn-sm btn-outline-primary" data-testid="wi-save" @click="saveWhatIf">Save as an alternative</button>
        </div>
      </div>
    </div>
  </section>
</template>
