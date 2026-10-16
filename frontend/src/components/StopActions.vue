<script setup>
// Per-stop edit buttons. They only QUEUE an operation; nothing is sent until the user applies the tray, and the schedule is never edited here.
import { computed, ref } from 'vue'
import { DAY_PARTS, DAY_PART_LABELS } from '../lib/replan.js'
const props = defineProps({ stop: { type: Object, required: true }, day: { type: Number, required: true }, totalDays: { type: Number, required: true }, name: { type: String, required: true }, locked: Boolean, disabled: Boolean })
const emit = defineEmits(['op'])
const moving = ref(false)
const moveDay = ref(props.day)
const moveTime = ref(props.stop.start)
const id = computed(() => props.stop.attraction_id)
const idp = computed(() => `mv-${id.value}`)
function queueMove() {
  emit('op', { op: 'move', attraction_id: id.value, day: Number(moveDay.value), start_time: moveTime.value })
  moving.value = false
}
</script>
<template>
  <div class="stop-actions mt-1" :data-testid="`actions-${id}`">
    <div class="d-flex flex-wrap align-items-center gap-1">
      <button v-if="!locked" type="button" class="btn btn-sm btn-outline-secondary" :disabled="disabled" :aria-label="`Lock ${stop.start}: ${name}, day ${day}`"
        @click="emit('op', { op: 'lock', attraction_id: id, day, start_time: stop.start })" data-testid="act-lock"><span aria-hidden="true">🔒</span> Lock {{ stop.start }}</button>
      <button v-else type="button" class="btn btn-sm btn-outline-secondary" :disabled="disabled" :aria-label="`Unlock ${name}`" @click="emit('op', { op: 'unlock', attraction_id: id })" data-testid="act-unlock"><span aria-hidden="true">🔓</span> Unlock</button>
      <details class="more-menu" :data-testid="`more-${id}`">
        <summary class="btn btn-sm btn-outline-secondary" :aria-label="`More actions for ${name}`"><span aria-hidden="true">⋯</span></summary>
        <div class="more-items">
          <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="disabled" :aria-expanded="moving" :aria-controls="idp" :aria-label="`Move ${name}`" @click="moving = !moving" data-testid="act-move">Move</button>
          <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="disabled" :aria-label="`Remove ${name} (skip this)`" @click="emit('op', { op: 'remove', attraction_id: id })" data-testid="act-remove">Skip this (remove)</button>
        </div>
      </details>
    </div>
    <form v-if="moving" :id="idp" class="card-soft mt-2 p-2" @submit.prevent="queueMove" :aria-label="`Move ${name}`">
      <div class="row g-2 align-items-end">
        <div class="col-6"><label class="form-label small mb-0" :for="`${idp}-d`">Day</label>
          <select :id="`${idp}-d`" class="form-select form-select-sm" v-model="moveDay"><option v-for="n in totalDays" :key="n" :value="n">Day {{ n }}</option></select></div>
        <div class="col-6"><label class="form-label small mb-0" :for="`${idp}-t`">Start time</label>
          <input :id="`${idp}-t`" class="form-control form-control-sm" type="time" v-model="moveTime" required /></div>
      </div>
      <div class="d-flex flex-wrap gap-1 mt-2" role="group" aria-label="Day-part shortcuts">
        <button v-for="(t, k) in DAY_PARTS" :key="k" type="button" class="btn btn-sm btn-outline-secondary" @click="moveTime = t">{{ DAY_PART_LABELS[k] }} ({{ t }})</button>
      </div>
      <div class="mt-2 d-flex gap-2"><button type="submit" class="btn btn-sm btn-primary">Queue move</button><button type="button" class="btn btn-sm btn-outline-secondary" @click="moving = false">Cancel</button></div>
    </form>
  </div>
</template>
