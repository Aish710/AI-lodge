<script setup>
// A small (i) that explains a term once. Keyboard focusable; the text is shown on hover and on focus, and is announced via aria-describedby.
import { useId } from 'vue'
defineProps({ text: { type: String, required: true }, label: { type: String, default: 'What does this mean?' } })
const id = `hint-${useId()}`
</script>
<template>
  <span class="hint-wrap">
    <button type="button" class="hint" :aria-label="label" :aria-describedby="id" data-testid="hint">i</button>
    <span :id="id" role="tooltip" class="hint-tip">{{ text }}</span>
  </span>
</template>
