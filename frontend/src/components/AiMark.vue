<script setup>
// Small provenance marker. Always TEXT ("AI" / "Calculated"), never colour alone. kind: 'ai' | 'calc'.
import { useId } from 'vue'
const props = defineProps({ kind: { type: String, default: 'ai' }, label: { type: String, default: '' } })
const id = `aim-${useId()}`
const TIP = { ai: 'Interpreted or written by the AI. Checked by code before it was shown.', calc: 'Calculated by code from the data. Not written by the AI.' }
</script>
<template>
  <span class="ai-mark" :class="props.kind === 'ai' ? 'ai-mark-ai' : 'ai-mark-calc'" :title="TIP[props.kind]" tabindex="0" :aria-describedby="id" :data-testid="props.kind === 'ai' ? 'ai-mark' : 'calc-mark'">
    {{ props.label || (props.kind === 'ai' ? 'AI' : 'Calculated') }}<span :id="id" class="visually-hidden"> ({{ TIP[props.kind] }})</span>
  </span>
</template>
