<script setup>
// The day-by-day plan as cards: a day card (weekday, stops, time at sights, travel, the day's cash cost, theme mix, one-line status), a light hotel
// card at each end, an event card per stop and a one-line travel connector between cards. Costs come from the server's cost_summary; this
// component never adds money up. Test ids of the old timeline are kept (timeline, day-N, stop-ID, locked-pill, free-day).
import { computed } from 'vue'
import SourceBadge from './SourceBadge.vue'
import { dayColor, dayShape } from '../lib/mapstyle.js'
import { flagText } from '../lib/rules.js'
import { formatPrice, humanMinutes, WEEKDAY_NAMES } from '../lib/format.js'
import { money } from '../lib/money.js'
import { dayMix, dayStatus, stopDuration, tags } from '../lib/tripView.js'
import { themeIcon, themeLabel } from '../lib/themes.js'

const props = defineProps({ days: { type: Array, required: true }, placesById: { type: Object, required: true }, fx: { type: Object, default: null }, hotelName: { type: String, default: 'the hotel' },
  lockedIds: { type: Array, default: () => [] }, votPerHour: { type: Number, default: null }, costDays: { type: Array, default: () => [] },
  selectedDay: { type: [String, Number], default: 'all' }, activeStop: { type: String, default: null } })
const emit = defineEmits(['hover-stop'])
const shown = computed(() => props.days.filter((d) => props.selectedDay === 'all' || d.day === props.selectedDay))
const costOf = (day) => props.costDays.find((c) => c.day === day) ?? null
const place = (s) => props.placesById[s.attraction_id]
const priceText = (s) => formatPrice(s.cost_status === 'unknown' ? null : s.cost, props.fx)
</script>
<template>
  <div class="stack" data-testid="timeline">
    <section v-for="d in shown" :key="d.day" class="day-block" :style="{ '--day': dayColor(d.day) }" :aria-label="`Day ${d.day}`" :data-testid="`day-${d.day}`">
      <header class="day-card" :data-testid="`day-card-${d.day}`">
        <h3 class="h6 mb-1">Day {{ d.day }} · {{ WEEKDAY_NAMES[d.weekday] }} <span class="muted fw-normal">({{ dayShape(d.day) }} markers)</span></h3>
        <ul v-if="d.stops.length && costOf(d.day)" class="day-facts list-unstyled mb-1" :data-testid="`day-facts-${d.day}`">
          <li>{{ d.stops.length }} {{ d.stops.length === 1 ? 'stop' : 'stops' }}</li>
          <li>At sights {{ humanMinutes(costOf(d.day).minutes_at_sights) }}</li>
          <li>Travel {{ humanMinutes(costOf(d.day).travel_minutes) }} <span class="muted">(estimated)</span></li>
          <li>Cash {{ money(costOf(d.day).day_total) }}<span v-if="costOf(d.day).unknown_price_ids.length" class="muted"> + {{ costOf(d.day).unknown_price_ids.length }} price(s) unknown</span></li>
        </ul>
        <p v-if="d.stops.length" class="small mb-0" :data-testid="`day-mix-${d.day}`">Day {{ d.day }}: {{ dayMix(d, placesById) }}. <span class="muted">{{ dayStatus(d) }}</span></p>
      </header>
      <p v-if="!d.stops.length" class="mb-0" data-testid="free-day">
        <strong>Day {{ d.day }} has no activities.</strong>
        <span class="muted"> The planner minimises true cost, and every day out adds a trip from and back to the hotel (travel time is valued at {{ votPerHour === null ? 'your value of time' : `${money(votPerHour)} an hour` }}), so a plan that uses fewer days can cost less. To use this day anyway, mark a sight as "Must visit" or lower your value of time.</span></p>
      <template v-else>
        <div class="hotel-card"><span aria-hidden="true">🏨</span> Leave {{ hotelName }} at {{ d.hotel_departure }}</div>
        <template v-for="(s, i) in d.stops" :key="s.attraction_id">
          <div class="connector" :data-testid="`connector-${d.day}-${i}`"><span aria-hidden="true">↓</span>
            Travel {{ humanMinutes(s.travel_minutes_from_previous) }} · {{ s.transport_jpy_from_previous === 0 ? 'no fare' : money(s.transport_jpy_from_previous) }} · estimated
            <span class="muted">{{ i === 0 ? '(from the hotel)' : '(from the previous stop)' }}</span></div>
          <article class="event-card" :class="{ 'is-active': activeStop === s.attraction_id }" :id="`timeline-stop-${s.attraction_id}`" tabindex="-1" :data-testid="`stop-${s.attraction_id}`"
            @mouseenter="emit('hover-stop', s.attraction_id)" @mouseleave="emit('hover-stop', null)" @focusin="emit('hover-stop', s.attraction_id)" @focusout="emit('hover-stop', null)">
            <span class="marker" :class="`shape-${dayShape(d.day)}`" aria-hidden="true"><span>{{ i + 1 }}</span></span>
            <div class="event-body">
              <div class="event-time" :data-testid="`time-${s.attraction_id}`">{{ s.start }}–{{ s.end }} <span class="muted">({{ humanMinutes(stopDuration(s)) }})</span></div>
              <div class="d-flex flex-wrap align-items-center gap-2">
                <strong>{{ place(s)?.name ?? s.attraction_id }}</strong>
                <span v-if="place(s)" class="pill" data-testid="event-theme"><span aria-hidden="true">{{ themeIcon(place(s)) }}</span> {{ themeLabel(place(s)) }}</span>
              </div>
              <div class="d-flex flex-wrap gap-1 mt-1" :data-testid="`tags-${s.attraction_id}`">
                <span v-if="tags(s, lockedIds).must" class="pill pill-must">Must visit</span>
                <span v-else class="pill">Include if it fits</span>
                <span v-if="tags(s, lockedIds).booking" class="pill" data-testid="tag-booking">Needs booking</span>
                <span v-if="tags(s, lockedIds).unknownHours" class="pill" data-testid="tag-unknown-hours">Unknown hours</span>
                <span v-if="tags(s, lockedIds).locked" class="pill" data-testid="locked-pill"><span aria-hidden="true">🔒</span> Locked</span>
              </div>
              <div class="leg mt-1" :data-testid="`cost-${s.attraction_id}`">
                Admission: <strong>{{ priceText(s) }}</strong>
                <template v-if="s.cost_status === 'unknown'"> <SourceBadge :status="null" what="price" /> <span>(not in the total)</span></template>
                <template v-else> <SourceBadge :status="place(s)?.source?.cost" what="price" /></template>
              </div>
              <slot name="actions" :stop="s" :day="d.day" :index="i" />
              <ul v-if="s.uncertainty_flags?.length" class="list-unstyled small mb-0" style="color: var(--amber)">
                <li v-for="f in s.uncertainty_flags" :key="f"><span aria-hidden="true">!</span> {{ flagText(f) }}</li>
              </ul>
            </div>
          </article>
        </template>
        <div class="connector" :data-testid="`connector-${d.day}-back`"><span aria-hidden="true">↓</span>
          Travel {{ humanMinutes(d.return_travel_minutes) }} · {{ d.return_transport_jpy === 0 ? 'no fare' : money(d.return_transport_jpy) }} · estimated <span class="muted">(back to the hotel)</span></div>
        <div class="hotel-card"><span aria-hidden="true">🏨</span> Back at {{ hotelName }} at {{ d.hotel_return }}</div>
      </template>
    </section>
  </div>
</template>
