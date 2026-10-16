<script setup>
// "Getting around": values the server already computed (cost_summary), shown together. Nothing is summed here. All travel figures are estimates.
import { computed } from 'vue'
import Hint from './Hint.vue'
import { humanMinutes } from '../lib/format.js'
import { money } from '../lib/money.js'
import { store } from '../store.js'
const cs = computed(() => store.plan?.cost_summary ?? null)
</script>
<template>
  <section v-if="cs" class="tile getting-around" aria-labelledby="ga-h" data-testid="getting-around">
    <h2 id="ga-h" class="tile-label">Getting around <span class="badge-src badge-estimated">estimated</span>
      <Hint text="Time moving between places, not time at sights. Estimated from distances in the sample data; there is no live transit." label="What does getting around mean?" /></h2>
    <dl class="ga-list mb-0">
      <div><dt>Travel time, all days</dt><dd data-testid="ga-total">{{ humanMinutes(cs.trip.travel_minutes) }}</dd></div>
      <div><dt>Average per day</dt><dd data-testid="ga-average">{{ humanMinutes(cs.trip.avg_travel_minutes_per_day) }}</dd></div>
      <div><dt>Transport cost</dt><dd data-testid="ga-transport">{{ money(cs.trip.transport) }}</dd></div>
      <div><dt>Hotel area</dt><dd data-testid="ga-area">{{ cs.trip.hotel_area }}</dd></div>
    </dl>
  </section>
</template>
