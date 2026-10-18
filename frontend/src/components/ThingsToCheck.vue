<script setup>
// ONE place for everything the plan could not verify, grouped by kind and naming the sights. The same fact is not repeated per day, per stop and in the totals line.
// Built only from the flags the server attached to the scheduled stops; nothing is inferred.
import { computed } from 'vue'
import { store } from '../store.js'
import { cleanHotelText as ct } from '../lib/names.js'

const props = defineProps({ days: { type: Array, required: true } })
const name = (id) => ct(store.placesById[id]?.name ?? id)
const groups = computed(() => {
  const by = { hours: [], price: [], booking: [] }
  for (const d of props.days) for (const s of d.stops ?? []) {
    const f = s.uncertainty_flags ?? []
    if (f.includes('opening_hours_unknown')) by.hours.push(s.attraction_id)
    if (f.includes('price_unknown')) by.price.push(s.attraction_id)
    if (f.includes('advance_booking_required')) by.booking.push(s.attraction_id)
  }
  return [
    by.hours.length && { key: 'hours', label: 'Opening hours unverified', text: 'the plan holds only if these are open at their scheduled time', ids: by.hours },
    by.price.length && { key: 'price', label: 'Admission price unknown', text: 'not in any total (never counted as free)', ids: by.price },
    by.booking.length && { key: 'booking', label: 'Advance booking required', text: 'book before you go', ids: by.booking },
  ].filter(Boolean)
})
</script>
<template>
  <section v-if="groups.length" class="small border rounded p-2 bg-white" data-testid="things-to-check" aria-labelledby="ttc-h">
    <h2 id="ttc-h" class="h6 mb-1">To check before you go</h2>
    <ul class="mb-1 ps-3">
      <li v-for="g in groups" :key="g.key" :data-testid="'check-' + g.key"><strong>{{ g.label }}:</strong> {{ g.ids.map(name).join(', ') }} <span class="muted">({{ g.text }})</span></li>
    </ul>
    <p class="muted mb-0">Hotels are fictional and travel times are estimates from straight-line distances; neither is verified. Confirm opening hours, prices and bookings with official sources.</p>
  </section>
</template>
