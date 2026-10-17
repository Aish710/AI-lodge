<script setup>
// Opt-in explanation (each click spends AI budget). SUPPORTING text only: numbers in the tables are the source of truth.
import { computed } from 'vue'
import { explanationBadge } from '../lib/rules.js'
import AiMark from './AiMark.vue'
import AiDrawer from './AiDrawer.vue'
const props = defineProps({ explanation: { type: Object, default: null }, busy: Boolean, disabled: Boolean, error: { type: Object, default: null }, title: { type: String, default: 'Explain this plan' } })
const emit = defineEmits(['explain'])
const badge = computed(() => explanationBadge(props.explanation))
</script>
<template>
  <section class="card-soft" aria-labelledby="exp-h" data-testid="explain-block">
    <h2 id="exp-h" class="h6 d-flex flex-wrap align-items-center gap-2">{{ title }} <AiMark v-if="explanation?.source === 'llm'" kind="ai" label="AI-written" /><AiMark v-else-if="explanation" kind="calc" label="Template" />
      <span v-if="explanation" class="badge-src" :class="badge.kind === 'llm' ? 'badge-verified' : 'badge-sample'" data-testid="explain-badge">{{ badge.label }}</span></h2>
    <button v-if="!explanation" type="button" class="btn btn-primary" :disabled="busy || disabled" @click="emit('explain')" data-testid="explain-button">
      {{ busy ? 'Writing the explanation…' : title }}</button>
    <p v-if="!explanation" class="small muted mt-2 mb-0">One click, one AI call. If the AI is off, you get a template summary. Warnings from the planner are always added by code.</p>
    <div v-if="error && !explanation" class="notice notice-warn mt-2" role="status"><span class="glyph" aria-hidden="true">!</span><span>{{ error.display }}</span></div>
    <template v-if="explanation">
      <p class="mt-2 mb-2" style="white-space: pre-line" data-testid="explain-text">{{ explanation.text }}</p>
      <div v-if="explanation.warnings?.length" class="notice notice-warn mb-2" role="note" data-testid="explain-warnings">
        <span class="glyph" aria-hidden="true">!</span>
        <div><strong>Warnings from the planner</strong><ul class="mb-0"><li v-for="w in explanation.warnings" :key="w">{{ w }}</li></ul></div>
      </div>
      <p class="small muted mb-1">Supporting text only; the tables are the source of truth.</p>
      <AiDrawer kind="explain" :result="explanation" class="mb-2" />
      <details class="small"><summary>How was this checked?</summary>
        <p class="mb-0 mt-1">The AI gets only this result's computed numbers and names, never place descriptions. Every number, time and name in its text is compared with them; on any mismatch its text is discarded and a template summary is shown.</p></details>
    </template>
  </section>
</template>
