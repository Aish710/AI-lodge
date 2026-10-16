<script setup>
// One wishlist card. Every field is rendered as PLAIN TEXT through Vue interpolation (escaped); the app never uses the raw-HTML directive,
// and the API does not even send the untrusted `description`.
import { computed } from 'vue'
import SourceBadge from './SourceBadge.vue'
import { formatPrice, formatHours1, humanMinutes, titleCase, UNKNOWN, WEEKDAY_NAMES, weekdayOfDay } from '../lib/format.js'
import { hoursWarnings } from '../lib/rules.js'
import { themeIcon, themeLabel } from '../lib/themes.js'

const props = defineProps({
  place: { type: Object, required: true }, state: { type: String, default: 'nice' },
  startWeekday: { type: Number, default: 0 }, days: { type: Number, default: 1 }, fx: { type: Object, default: null },
  compact: { type: Boolean, default: false },
  highlight: { type: Boolean, default: false },  // the sight's theme matches the traveller's interests (a highlight only)  // Plan screen grid: opening hours tuck into a disclosure
})
const emit = defineEmits(['update:state'])
const warnings = computed(() => hoursWarnings(props.place, props.startWeekday, props.days))
const hoursByDay = computed(() => Array.from({ length: props.days }, (_, i) => {
  const wd = weekdayOfDay(props.startWeekday, i + 1)
  return { day: i + 1, name: WEEKDAY_NAMES[wd].slice(0, 3), text: formatHours1(props.place.opening_hours?.[wd]) }
}))
const choices = [['must', 'Must visit'], ['nice', 'Include if it fits'], ['skip', 'Not interested']]
const gid = computed(() => `wish-${props.place.id}`)
</script>
<template>
  <article class="card-soft h-100 d-flex flex-column gap-2" :data-testid="`card-${place.id}`" :data-state="state">
    <div class="d-flex justify-content-between align-items-start gap-2">
      <h3 class="h6 mb-0">{{ place.name }}</h3>
      <SourceBadge :status="place.source?.record" what="record" />
    </div>
    <div class="small muted">{{ place.area }} · {{ titleCase(place.category) }} · {{ place.indoor ? 'Indoor' : 'Outdoor' }}</div>
    <dl class="small mb-0 row g-1">
      <dt class="col-5 fw-normal muted">Time needed</dt><dd class="col-7 mb-0">{{ humanMinutes(place.duration_minutes) }}</dd>
      <dt class="col-5 fw-normal muted">Admission</dt>
      <dd class="col-7 mb-0">{{ formatPrice(place.admission_cost, fx) }} <SourceBadge :status="place.admission_cost === null ? null : place.source?.cost" what="price" /></dd>
      <template v-if="!compact">
        <dt class="col-5 fw-normal muted">Hours</dt>
        <dd class="col-7 mb-0">
          <span v-for="h in hoursByDay" :key="h.day" class="d-block">Day {{ h.day }} {{ h.name }}: {{ h.text }}</span>
          <SourceBadge :status="place.source?.hours" what="hours" />
        </dd>
      </template>
    </dl>
    <details v-if="compact" class="small"><summary>Opening hours</summary>
      <span v-for="h in hoursByDay" :key="h.day" class="d-block">Day {{ h.day }} {{ h.name }}: {{ h.text }}</span>
      <SourceBadge :status="place.source?.hours" what="hours" />
    </details>
    <div class="d-flex flex-wrap gap-1">
      <span class="pill" data-testid="theme-tag"><span aria-hidden="true">{{ themeIcon(place) }}</span> {{ themeLabel(place) }}</span>
      <span v-if="highlight" class="pill pill-must" data-testid="interest-tag">Matches your interests</span>
      <span v-if="place.advance_booking_required" class="pill">Booking required</span>
    </div>
    <ul v-if="warnings.length" class="list-unstyled small mb-0" data-testid="hours-warnings">
      <li v-for="w in warnings" :key="w.day" class="text-warning-emphasis" style="color: var(--amber)">
        <span aria-hidden="true">!</span>
        <template v-if="w.kind === 'closed'"> Closed on day {{ w.day }} ({{ w.weekday }}): it will not be scheduled that day.</template>
        <template v-else> Hours unknown on day {{ w.day }} ({{ w.weekday }}): never assumed open, so it is only scheduled if you allow unknown hours.</template>
      </li>
    </ul>
    <div class="mt-auto pt-1">
      <div class="seg" role="radiogroup" :aria-label="`${place.name}: how much do you want it?`">
        <template v-for="[val, label] in choices" :key="val">
          <input type="radio" :id="`${gid}-${val}`" :name="gid" :value="val" :checked="state === val" @change="emit('update:state', val)" />
          <label :for="`${gid}-${val}`" :title="val === 'nice' ? 'Left out if it adds too much travel' : undefined">{{ label }}</label>
        </template>
      </div>
    </div>
  </article>
</template>
