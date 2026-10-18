<script setup>
// Empty days: say what the validated plan shows, then offer three honest choices. Nothing here promises a feasible plan; each option is a PREVIEW that the planner solves and the validator checks.
import { computed, ref, watch } from 'vue'
import { store, previewProposal, solverBusy, rateLimited } from '../store.js'
import { cleanHotelText as ct } from '../lib/names.js'

const kept = ref(false)
const days = computed(() => store.plan?.result?.days ?? [])
const empty = computed(() => days.value.filter((d) => !d.stops.length).map((d) => d.day))
const scheduled = computed(() => new Set(days.value.flatMap((d) => d.stops.map((s) => s.attraction_id))))
const unscheduled = computed(() => Object.keys(store.placesById).filter((id) => !scheduled.value.has(id) && store.wishlist[id] !== 'skip'))
const busy = computed(() => solverBusy.value || rateLimited.value)
const dayList = computed(() => empty.value.map((n) => `Day ${n}`).join(', '))
watch(() => store.plan, () => { kept.value = false })
async function spread() { await previewProposal({ kind: 'whatif', patch: { minActive: days.value.length } }); scroll() }
async function add(id) { await previewProposal({ kind: 'whatif', patch: { addMust: [id] } }); scroll() }
function scroll() { const t = document.querySelector('[data-testid="whatif"]'); t?.scrollIntoView({ behavior: 'smooth', block: 'start' }); t?.focus?.({ preventScroll: true }) }
</script>
<template>
  <section v-if="empty.length && !kept" class="notice notice-info" data-testid="empty-days" aria-labelledby="ed-h">
    <span class="glyph" aria-hidden="true">i</span>
    <div class="w-100">
      <h2 id="ed-h" class="h6 mb-1">{{ dayList }} {{ empty.length === 1 ? 'has' : 'have' }} no sights</h2>
      <p class="small mb-2" data-testid="ed-evidence">
        The plan uses {{ days.length - empty.length }} of {{ days.length }} days. The planner is not required to fill every day: it only adds a sight when that is worth its cost, travel time and your limits, or when no more sights were available. This is the solver's result, not proof of one cause.
        <template v-if="unscheduled.length">{{ unscheduled.length }} sight{{ unscheduled.length === 1 ? ' is' : 's are' }} in this city's data but not in the plan.</template>
        <template v-else>Every sight in this city's data is already in the plan or marked not interested.</template>
      </p>
      <div class="d-flex flex-wrap gap-2 mb-2">
        <button type="button" class="btn btn-sm btn-outline-secondary" data-testid="ed-keep" @click="kept = true">Keep the free days</button>
        <button type="button" class="btn btn-sm btn-outline-primary" :disabled="busy || !unscheduled.length && days.length - empty.length < 1" data-testid="ed-spread" @click="spread">Preview spreading the sights over every day</button>
      </div>
      <div v-if="unscheduled.length">
        <div class="small fw-semibold mb-1">Or consider adding one of these (preview only, from the city's data):</div>
        <div class="d-flex flex-wrap gap-2">
          <button v-for="id in unscheduled.slice(0, 5)" :key="id" type="button" class="btn btn-sm btn-outline-primary" :disabled="busy" :data-testid="'ed-add-' + id" @click="add(id)">{{ ct(store.placesById[id]?.name ?? id) }}</button>
        </div>
      </div>
      <p class="small muted mt-2 mb-0">A preview is solved and independently checked, and may find that nothing fits. Your plan only changes when you press Apply.</p>
    </div>
  </section>
</template>
