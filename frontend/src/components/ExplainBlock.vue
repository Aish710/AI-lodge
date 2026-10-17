<script setup>
// Opt-in explanation (each click spends AI budget). SUPPORTING text only: numbers in the tables are the source of truth.
import { computed, onBeforeUnmount, ref } from 'vue'
import { explanationBadge } from '../lib/rules.js'
import { store } from '../store.js'
import { clearHighlights, highlightFact } from '../lib/citations.js'
import { WOULD_ADD } from '../lib/aiOff.js'
import AiMark from './AiMark.vue'
import AiDrawer from './AiDrawer.vue'
const props = defineProps({ explanation: { type: Object, default: null }, busy: Boolean, disabled: Boolean, error: { type: Object, default: null }, title: { type: String, default: 'Explain this plan' } })
const emit = defineEmits(['explain'])
const badge = computed(() => explanationBadge(props.explanation))
const factText = computed(() => Object.fromEntries((props.explanation?.facts ?? []).map((f) => [f.id, f.text])))
const active = ref(null)           // the chip being hovered or focused: its fact text is shown, and the cited number is outlined in the tables
const show = (id) => { active.value = id; highlightFact(factText.value[id] ?? '') }
const hide = () => { active.value = null; clearHighlights() }
onBeforeUnmount(clearHighlights)
</script>
<template>
  <section class="card-soft" aria-labelledby="exp-h" data-testid="explain-block">
    <h2 id="exp-h" class="h6 d-flex flex-wrap align-items-center gap-2">{{ title }} <AiMark v-if="explanation?.source === 'llm'" kind="ai" label="AI-written" /><AiMark v-else-if="explanation" kind="calc" label="Template" />
      <span v-if="explanation" class="badge-src" :class="badge.kind === 'llm' ? 'badge-verified' : 'badge-sample'" data-testid="explain-badge">{{ badge.label }}</span></h2>
    <div v-if="store.aiOff && !explanation" class="notice notice-info" role="status" data-testid="explain-ai-off"><span class="glyph" aria-hidden="true">i</span><span>AI off. {{ WOULD_ADD.explain }}</span></div>
    <button v-else-if="!explanation" type="button" class="btn btn-primary" :disabled="busy || disabled" @click="emit('explain')" data-testid="explain-button">
      {{ busy ? 'Writing the explanation…' : title }}</button>
    <p v-if="!explanation && !store.aiOff" class="small muted mt-2 mb-0">One click, one AI call. If the AI is off, you get a template summary. Warnings from the planner are always added by code.</p>
    <div v-if="error && !explanation" class="notice notice-warn mt-2" role="status"><span class="glyph" aria-hidden="true">!</span><span>{{ error.display }}</span></div>
    <template v-if="explanation">
      <div v-if="explanation.cited" class="mt-2 mb-2" data-testid="explain-cited">
        <p class="mb-1" data-testid="explain-text"><template v-for="(s, i) in explanation.sentences" :key="i"><span>{{ s.text }}</span>
          <button v-for="id in s.fact_ids" :key="id" type="button" class="cite-chip" :data-testid="`cite-${id}`" :aria-label="`Source ${id}: ${factText[id]}`" :aria-describedby="active === id ? 'cite-source' : undefined"
            @mouseenter="show(id)" @mouseleave="hide" @focus="show(id)" @blur="hide" @keydown.esc="hide">{{ id }}</button>{{ ' ' }}</template></p>
        <p id="cite-source" class="small mb-1" role="status" aria-live="polite" data-testid="cite-source"><template v-if="active"><strong>{{ active }}:</strong> {{ factText[active] }}</template><template v-else>Each sentence names the facts it rests on (F1, F2, ...). Hover or focus a chip to see the fact and where its number is in the tables.</template></p>
        <details class="small"><summary>The facts the sentences rest on</summary><ul class="mb-0 mt-1" data-testid="cite-facts"><li v-for="f in explanation.facts" :key="f.id"><strong>{{ f.id }}:</strong> {{ f.text }}</li></ul></details>
        <p v-if="explanation.dropped" class="small muted mb-0" data-testid="cite-dropped">{{ explanation.dropped }} sentence(s) written by the AI were left out because code could not tie them to the facts.</p>
      </div>
      <p v-else class="mt-2 mb-2" style="white-space: pre-line" data-testid="explain-text">{{ explanation.text }}</p>
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
