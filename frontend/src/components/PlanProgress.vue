<script setup>
// Staged progress for "Plan my trip" and for a hotel switch. Only stages that really happen are named: the comparison request, then the
// planning request, whose answer already includes the independent validator's checks.
import { computed } from 'vue'
import { cancelPlanning, store } from '../store.js'
const props = defineProps({ switching: { type: Boolean, default: false } })
const steps = computed(() => (props.switching
  ? [{ id: 'planning', label: 'Planning your days and checking the plan…' }]
  : [{ id: 'comparing', label: 'Comparing hotels…' }, { id: 'planning', label: 'Planning your days and checking the plan…' }]))
const index = computed(() => steps.value.findIndex((x) => x.id === store.stage))
</script>
<template>
  <div v-if="store.stage" class="plan-progress" role="status" aria-live="polite" data-testid="plan-progress">
    <span class="spinner" aria-hidden="true"></span>
    <ol class="list-unstyled mb-0 d-flex flex-wrap gap-3">
      <li v-for="(st, i) in steps" :key="st.id" :class="{ 'fw-bold': i === index, muted: i > index }" :aria-current="i === index ? 'step' : undefined">
        <span aria-hidden="true">{{ i < index ? '✓' : i === index ? '…' : '·' }}</span> {{ st.label }}
      </li>
    </ol>
    <button type="button" class="btn btn-sm btn-outline-secondary" @click="cancelPlanning" data-testid="cancel-plan">Cancel</button>
  </div>
</template>
