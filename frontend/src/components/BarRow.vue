<script setup>
// A labelled horizontal bar. Pure CSS. The value is always printed as text too (a bar is never the only cue).
import { computed } from 'vue'
const props = defineProps({ label: String, value: { type: Number, default: 0 }, max: { type: Number, default: 100 }, text: String, tone: { type: String, default: 'good' } })
const pct = computed(() => (props.max > 0 ? Math.max(0, Math.min(100, (props.value / props.max) * 100)) : 0))
</script>
<template>
  <div class="mb-2" data-testid="bar-row">
    <div class="d-flex justify-content-between small"><span>{{ label }}</span><strong>{{ text }}</strong></div>
    <div class="bar-track" role="img" :aria-label="`${label}: ${text}`"><div class="bar-fill" :class="tone === 'bad' ? 'bar-bad' : tone === 'warn' ? 'bar-warn' : ''" :style="{ width: pct + '%' }"></div></div>
  </div>
</template>
