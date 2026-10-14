<script setup>
import SourceBadge from './SourceBadge.vue'
import { dayColor, dayShape } from '../lib/mapstyle.js'
import { flagText } from '../lib/rules.js'
import { formatMoney, humanMinutes, WEEKDAY_NAMES, UNKNOWN } from '../lib/format.js'
import { money } from '../lib/money.js'
import { toMinutes } from '../lib/time.js'
defineProps({ days: { type: Array, required: true }, placesById: { type: Object, required: true }, fx: { type: Object, default: null }, hotelName: { type: String, default: 'the hotel' },
  lockedIds: { type: Array, default: () => [] }, votPerHour: { type: Number, default: null } })
const dur = (s) => toMinutes(s.end) - toMinutes(s.start)
</script>
<template>
  <div class="stack" data-testid="timeline">
    <section v-for="d in days" :key="d.day" class="day-block" :style="{ '--day': dayColor(d.day) }" :aria-label="`Day ${d.day}`" :data-testid="`day-${d.day}`">
      <h3 class="h6 mb-1">Day {{ d.day }} · {{ WEEKDAY_NAMES[d.weekday] }} <span class="muted fw-normal">({{ dayShape(d.day) }} markers)</span></h3>
      <p v-if="!d.stops.length" class="mb-0" data-testid="free-day">
        <strong>Day {{ d.day }} has no activities.</strong>
        <span class="muted"> The planner minimises true cost, and every day out adds a trip from and back to the hotel (travel time is valued at {{ votPerHour === null ? 'your value of time' : `¥${votPerHour.toLocaleString('en-US')} an hour` }}), so a plan that uses fewer days can cost less. To use this day anyway, mark a sight as "Must visit" or lower your value of time.</span></p>
      <template v-else>
        <div class="leg">Leave {{ hotelName }} at {{ d.hotel_departure }}</div>
        <div v-for="(s, i) in d.stops" :key="s.attraction_id" class="stop" :id="`timeline-stop-${s.attraction_id}`" tabindex="-1" :data-testid="`stop-${s.attraction_id}`">
          <span class="marker" :class="`shape-${dayShape(d.day)}`" aria-hidden="true"><span>{{ i + 1 }}</span></span>
          <div>
            <div class="d-flex flex-wrap align-items-center gap-2">
              <strong>{{ placesById[s.attraction_id]?.name ?? s.attraction_id }}</strong>
              <span v-if="s.is_must_visit" class="pill pill-must">Must visit</span>
              <span v-if="lockedIds.includes(s.attraction_id)" class="pill" data-testid="locked-pill"><span aria-hidden="true">🔒</span> Locked</span>
            </div>
            <div>{{ s.start }}–{{ s.end }} <span class="muted">({{ humanMinutes(dur(s)) }})</span></div>
            <div class="leg">
              {{ humanMinutes(s.travel_minutes_from_previous) }} travel{{ i === 0 ? ' from the hotel' : ' from the previous stop' }},
              {{ money(s.transport_jpy_from_previous) }} fare <SourceBadge status="estimated" what="travel" />
            </div>
            <div class="leg">
              Admission:
              <template v-if="s.cost_status === 'unknown'">{{ UNKNOWN }} <SourceBadge :status="null" what="price" /> <span>(not in the total)</span></template>
              <template v-else>{{ formatMoney(s.cost, fx) }} <SourceBadge :status="placesById[s.attraction_id]?.source?.cost" what="price" /></template>
            </div>
            <slot name="actions" :stop="s" :day="d.day" :index="i" />
            <ul v-if="s.uncertainty_flags?.length" class="list-unstyled small mb-0" style="color: var(--amber)">
              <li v-for="f in s.uncertainty_flags" :key="f"><span aria-hidden="true">!</span> {{ flagText(f) }}</li>
            </ul>
          </div>
        </div>
        <div class="leg">Back at {{ hotelName }} at {{ d.hotel_return }} ({{ humanMinutes(d.return_travel_minutes) }}, {{ money(d.return_transport_jpy) }} fare, estimated)</div>
      </template>
    </section>
  </div>
</template>
