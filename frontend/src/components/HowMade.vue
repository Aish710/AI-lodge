<script setup>
// Makes the AI's role visible without text: who planned it, who checked it, and (only if it was used) who explained it.
import { computed } from 'vue'
const props = defineProps({ explained: { type: String, default: null } })   // 'llm' | 'template' | null
const steps = computed(() => [
  { key: 'plan', label: 'Planned by the optimiser' },
  { key: 'check', label: 'Checked by the validator' },
  ...(props.explained === 'llm' ? [{ key: 'ai', label: 'Explained by AI, number-checked' }] : []),
])
</script>
<template>
  <ol class="how-made" aria-label="How this result was made" data-testid="how-made">
    <li v-for="(s, i) in steps" :key="s.key" :data-step="s.key"><span v-if="i" class="how-arrow" aria-hidden="true">›</span><span class="how-chip">{{ s.label }}</span></li>
  </ol>
</template>
