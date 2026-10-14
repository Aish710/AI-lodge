<script setup>
// Decision 3: a skipped optional sight is a visible decision, not a bug. Must-visits are never listed here: if one cannot be placed,
// the conflict panel explains why.
import { computed } from 'vue'
import { notScheduledItems } from '../lib/rules.js'
import { money } from '../lib/money.js'
const props = defineProps({ missedIds: { type: Array, default: () => [] }, placesById: { type: Object, required: true }, penaltyJpy: { type: Number, default: null } })
const items = computed(() => notScheduledItems(props.missedIds, props.placesById, props.penaltyJpy))
</script>
<template>
  <section class="card-soft" aria-labelledby="ns-h" data-testid="not-scheduled">
    <h2 id="ns-h" class="h5">Not scheduled</h2>
    <p v-if="!items.length" class="mb-0">Every optional sight that can be visited is in the plan.</p>
    <template v-else>
      <p class="mb-2">These optional sights were left out on purpose. Each one was considered and skipped.</p>
      <ul class="mb-2" data-testid="skipped-list">
        <li v-for="it in items" :key="it.id"><strong>{{ it.name }}</strong>: {{ it.reason }}</li>
      </ul>
      <p v-if="penaltyJpy !== null" class="small muted mb-0" data-testid="penalty-note">
        The planner charges {{ money(penaltyJpy) }} for each optional sight it leaves out and skips one only when visiting it costs more than that in travel time, fares and admission. To include a sight anyway, mark it "Must visit".
      </p>
    </template>
  </section>
</template>
