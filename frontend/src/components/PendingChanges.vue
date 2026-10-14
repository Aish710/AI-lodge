<script setup>
// The pending-changes tray: operations queue up here and go to /replan in ONE call when the user clicks "Apply changes".
import { computed, ref } from 'vue'
import { describeOp, MAX_OPS } from '../lib/replan.js'
import { cityCurrency } from '../lib/money.js'
const props = defineProps({ queue: { type: Array, required: true }, placesById: { type: Object, required: true }, hotelsById: { type: Object, required: true },
  hotelChoices: { type: Array, default: () => [] }, currentHotel: { type: String, default: null }, busy: Boolean, disabled: Boolean, error: { type: String, default: null }, budgetNow: { type: Number, default: null } })
const emit = defineEmits(['remove', 'clear', 'apply', 'op'])
const budget = ref(props.budgetNow ?? '')
const strict = ref(false)
const hotel = ref('')
const others = computed(() => props.hotelChoices.filter((h) => h !== props.currentHotel))
const budgetOk = computed(() => budget.value !== '' && Number(budget.value) >= 0)
function queueBudget() { emit('op', { op: 'change_budget', budget: Math.round(Number(budget.value)), strict: strict.value }) }
function queueHotel() { if (hotel.value) { emit('op', { op: 'switch_hotel', hotel_id: hotel.value }); hotel.value = '' } }
</script>
<template>
  <section class="card-soft" aria-labelledby="pending-h" data-testid="pending-tray">
    <h2 id="pending-h" class="h5">Pending changes <span class="pill" data-testid="pending-count">{{ queue.length }} of {{ MAX_OPS }}</span></h2>
    <p v-if="!queue.length" class="muted mb-2">Nothing queued. Use the buttons on a stop, or the options below, then apply everything in one go. Nothing changes until you click "Apply changes".</p>
    <template v-else>
      <p class="mb-1">This is exactly what will be sent to the planner:</p>
      <ol class="mb-2" data-testid="pending-list">
        <li v-for="(o, i) in queue" :key="i" class="mb-1">
          {{ describeOp(o, placesById, hotelsById, cityCurrency()) }}
          <button type="button" class="btn btn-sm btn-link p-0 ms-2" :aria-label="`Remove from queue: ${describeOp(o, placesById, hotelsById, cityCurrency())}`" @click="emit('remove', i)" data-testid="unqueue">remove</button>
        </li>
      </ol>
    </template>
    <div v-if="error" class="notice notice-warn mb-2" role="alert"><span class="glyph" aria-hidden="true">!</span><span>{{ error }}</span></div>
    <div class="d-flex flex-wrap gap-2 mb-3">
      <button type="button" class="btn btn-primary" :disabled="!queue.length || busy || disabled" @click="emit('apply')" data-testid="apply-changes">{{ busy ? 'Applying…' : `Apply changes (${queue.length})` }}</button>
      <button type="button" class="btn btn-outline-secondary" :disabled="!queue.length || busy" @click="emit('clear')" data-testid="clear-queue">Undo queued changes</button>
    </div>
    <details>
      <summary class="fw-semibold">More changes: budget and hotel</summary>
      <div class="row g-3 mt-1">
        <form class="col-12 col-md-6" @submit.prevent="queueBudget" aria-label="Change budget">
          <label class="form-label" for="pc-budget">Budget for sights and transport ({{ cityCurrency() }})</label>
          <div class="input-group"><input id="pc-budget" class="form-control" type="number" min="0" v-model="budget" /><button class="btn btn-outline-secondary" type="submit" :disabled="!budgetOk">Queue</button></div>
          <div class="form-check mt-1"><input id="pc-strict" class="form-check-input" type="checkbox" v-model="strict" /><label class="form-check-label" for="pc-strict">Strict limit (never exceed)</label></div>
        </form>
        <form class="col-12 col-md-6" @submit.prevent="queueHotel" aria-label="Switch hotel">
          <label class="form-label" for="pc-hotel">Switch hotel</label>
          <div class="input-group">
            <select id="pc-hotel" class="form-select" v-model="hotel"><option value="">Choose a compared hotel…</option><option v-for="h in others" :key="h" :value="h">{{ hotelsById[h]?.name ?? h }}</option></select>
            <button class="btn btn-outline-secondary" type="submit" :disabled="!hotel">Queue</button>
          </div>
          <div v-if="!others.length" class="form-text">Compare at least two hotels first to switch between them.</div>
        </form>
      </div>
    </details>
  </section>
</template>
