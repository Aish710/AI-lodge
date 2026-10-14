<script setup>
// Opt-in explanation (each click spends AI budget). SUPPORTING text only: numbers in the tables are the source of truth.
import { computed } from 'vue'
import { explanationBadge } from '../lib/rules.js'
const props = defineProps({ explanation: { type: Object, default: null }, busy: Boolean, disabled: Boolean, error: { type: Object, default: null } })
const emit = defineEmits(['explain'])
const badge = computed(() => explanationBadge(props.explanation))
</script>
<template>
  <section class="card-soft" aria-labelledby="exp-h" data-testid="explain-block">
    <h2 id="exp-h" class="h6 d-flex flex-wrap align-items-center gap-2">Explain this result
      <span v-if="explanation" class="badge-src" :class="badge.kind === 'llm' ? 'badge-verified' : 'badge-sample'" data-testid="explain-badge">{{ badge.label }}</span></h2>
    <button v-if="!explanation" type="button" class="btn btn-sm btn-outline-primary" :disabled="busy || disabled" @click="emit('explain')" data-testid="explain-button">
      {{ busy ? 'Writing the explanation…' : 'Explain this result' }}</button>
    <p v-if="!explanation" class="small muted mt-2 mb-0">Optional. Uses the AI if available; otherwise a template summary.</p>
    <div v-if="error && !explanation" class="notice notice-warn mt-2" role="status"><span class="glyph" aria-hidden="true">!</span><span>{{ error.display }}</span></div>
    <template v-if="explanation">
      <p class="mt-2 mb-2" style="white-space: pre-line" data-testid="explain-text">{{ explanation.text }}</p>
      <div v-if="explanation.warnings?.length" class="notice notice-warn mb-2" role="note" data-testid="explain-warnings">
        <span class="glyph" aria-hidden="true">!</span>
        <div><strong>Warnings from the planner</strong><ul class="mb-0"><li v-for="w in explanation.warnings" :key="w">{{ w }}</li></ul></div>
      </div>
      <p class="small muted mb-1">Supporting text only; the tables are the source of truth.</p>
      <details class="small"><summary>How was this checked?</summary>
        <p class="mb-0 mt-1">The AI gets only this result's computed numbers and names, never place descriptions. Every number, time and name in its text is compared with them; on any mismatch its text is discarded and a template summary is shown.</p></details>
    </template>
  </section>
</template>
