<script setup>
// Day chips: Day 1 | Day 2 | ... | All. A selected day shows only its pins, route and cards. Selected state is shown by text ("selected") and style, not colour alone.
import { computed } from 'vue'
import { store } from '../store.js'
const props = defineProps({ days: { type: Array, required: true } })
const options = computed(() => [...props.days.map((d) => ({ id: d.day, label: `Day ${d.day}` })), { id: 'all', label: 'All days' }])
function onKey(e, i) {
  const n = options.value.length
  const to = e.key === 'ArrowRight' ? (i + 1) % n : e.key === 'ArrowLeft' ? (i + n - 1) % n : e.key === 'Home' ? 0 : e.key === 'End' ? n - 1 : null
  if (to === null) return
  e.preventDefault()
  store.selectedDay = options.value[to].id
  document.getElementById(`daychip-${options.value[to].id}`)?.focus()
}
</script>
<template>
  <div class="day-chips" role="tablist" aria-label="Show one day or all days" data-testid="day-selector">
    <button v-for="(o, i) in options" :key="o.id" :id="`daychip-${o.id}`" type="button" role="tab" class="day-chip" :aria-selected="store.selectedDay === o.id" :tabindex="store.selectedDay === o.id ? 0 : -1"
      :data-testid="`daychip-${o.id}`" @click="store.selectedDay = o.id" @keydown="onKey($event, i)">
      <span v-if="store.selectedDay === o.id" aria-hidden="true">✓ </span>{{ o.label }}<span v-if="store.selectedDay === o.id" class="sr-only"> (selected)</span>
    </button>
  </div>
</template>
