<script setup>
// The compared hotels as one segmented choice. Best value is pre-selected by the planner; choosing another re-plans in place.
// Native radio inputs: arrow keys move between hotels, the choice is announced, and it works at 320 px (long names wrap).
import { computed } from 'vue'
import { store, switchHotel, solverBusy, rateLimited } from '../store.js'
import { formatLocalMoney } from '../lib/format.js'
import { cleanHotelText as ct } from '../lib/names.js'

const results = computed(() => store.comparison?.results ?? [])
const best = computed(() => store.comparison?.best_by_true_cost ?? null)
const money = (v) => formatLocalMoney(v, store.city?.currency_code ?? 'JPY')
const disabled = computed(() => solverBusy.value || rateLimited.value)
</script>
<template>
  <fieldset v-if="results.length" class="hotel-switch" data-testid="hotel-switch" :disabled="disabled">
    <legend class="h6 mb-2">Hotel <span class="muted fw-normal small">(demo hotels with sample prices)</span></legend>
    <div class="hotel-switch-options" role="radiogroup" aria-label="Hotel for this plan">
      <template v-for="r in results" :key="r.hotel_id">
        <input type="radio" class="hotel-switch-input" name="hotel-switch" :id="`hs-${r.hotel_id}`" :value="r.hotel_id" :checked="store.chosenHotel === r.hotel_id"
          :disabled="!r.feasible" @change="switchHotel(r.hotel_id)" :data-testid="`switch-${r.hotel_id}`" />
        <label class="hotel-switch-option" :for="`hs-${r.hotel_id}`">
          <span class="hotel-title">{{ ct(r.hotel_name) }}</span>
          <span class="small muted">{{ money(r.nightly_rate_jpy) }}/night</span>
          <span v-if="r.hotel_id === best" class="pill pill-must">Best value</span>
          <span v-if="!r.feasible" class="small">No feasible plan</span>
        </label>
      </template>
    </div>
  </fieldset>
</template>
