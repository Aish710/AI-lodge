<script setup>
import { costTerms } from '../lib/costTerms.js'
// Opt-in explanation (each click spends AI budget). SUPPORTING text only: numbers in the tables are the source of truth.
import { computed, onBeforeUnmount, ref, useId } from 'vue'
import { explanationBadge } from '../lib/rules.js'
import { store } from '../store.js'
import { clearHighlights, highlightFact } from '../lib/citations.js'
import { WOULD_ADD } from '../lib/aiOff.js'
import AiMark from './AiMark.vue'
import AiDrawer from './AiDrawer.vue'
import ThingsToCheck from './ThingsToCheck.vue'
import { aiOutcome, rejectionText } from '../lib/planSummary.js'
// `summary` (from lib/planSummary.js) switches on the plan-first layout: a code-written summary is the main content, AI wording is an optional extra, diagnostics are folded away.
const props = defineProps({ explanation: { type: Object, default: null }, busy: Boolean, disabled: Boolean, error: { type: Object, default: null }, title: { type: String, default: 'Tell me why!' }, summary: { type: Object, default: null }, days: { type: Array, default: () => [] } })
const headingId = useId(), citeId = useId()
const emit = defineEmits(['explain'])
const badge = computed(() => explanationBadge(props.explanation))
const outcome = computed(() => aiOutcome(props.explanation))
const rejected = computed(() => (props.explanation?.grounding?.rejected_tokens ?? []).map(rejectionText))
const factText = computed(() => Object.fromEntries((props.explanation?.facts ?? []).map((f) => [f.id, f.text])))
const active = ref(null)           // the chip being hovered or focused: its fact text is shown, and the cited number is outlined in the tables
const show = (id) => { active.value = id; highlightFact(factText.value[id] ?? '') }
const hide = () => { active.value = null; clearHighlights() }
onBeforeUnmount(clearHighlights)
</script>
<template>
  <section v-if="summary" class="card-soft" :aria-labelledby="headingId" data-testid="explain-block">
    <h2 :id="headingId" class="h5 d-flex flex-wrap align-items-center gap-2">Your plan in plain words <AiMark kind="calc" />
      <span v-if="explanation" class="badge-src" :class="badge.kind === 'llm' ? 'badge-verified' : 'badge-sample'" data-testid="explain-badge">{{ badge.label }}</span></h2>
    <p class="mb-2" :class="{ 'text-danger': summary.status.kind === 'bad' }" data-testid="plan-status"><strong>{{ summary.status.text }}</strong></p>
    <ul class="mb-2 ps-3" data-testid="plan-summary"><li v-for="l in summary.lines" :key="l.key" :data-testid="'summary-' + l.key"><strong>{{ l.label }}:</strong> {{ l.text }}</li></ul>
    <div data-testid="explain-warnings" class="mb-2"><ThingsToCheck embedded :days="days" /></div>

    <div v-if="explanation?.source === 'llm'" class="mt-2 mb-2" data-testid="explain-ai">
      <h3 class="h6">In the AI's words <AiMark kind="ai" label="AI-written" /></h3>
      <p v-if="explanation.cited" class="mb-1" data-testid="explain-text"><template v-for="(s, i) in explanation.sentences" :key="i"><span>{{ costTerms(s.text) }}</span>
        <button v-for="id in s.fact_ids" :key="id" type="button" class="cite-chip" :data-testid="`cite-${id}`" :aria-label="`Source ${id}: ${costTerms(factText[id])}`" @mouseenter="show(id)" @mouseleave="hide" @focus="show(id)" @blur="hide" @keydown.esc="hide">{{ id }}</button>{{ ' ' }}</template></p>
      <p v-else class="mb-1" style="white-space: pre-line" data-testid="explain-text">{{ costTerms(explanation.text) }}</p>
      <p :id="citeId" class="small mb-1" role="status" aria-live="polite" data-testid="cite-source"><template v-if="active"><strong>{{ active }}:</strong> {{ costTerms(factText[active]) }}</template></p>
    </div>
    <div v-else-if="outcome.state === 'rejected'" class="notice notice-info small" role="status" data-testid="explain-fallback"><span class="glyph" aria-hidden="true">i</span><span>The AI was asked to put this in words, but its wording was not used because a check failed. The summary above is complete and does not depend on it.</span></div>

    <div v-if="store.aiOff" class="small muted" data-testid="explain-ai-off">AI off. {{ WOULD_ADD.explain }}</div>
    <template v-else-if="!explanation">
      <button type="button" class="btn btn-outline-primary btn-sm" :disabled="busy || disabled" @click="emit('explain')" data-testid="explain-button">{{ busy ? 'Writing the explanation…' : title }}</button>
      <span class="small muted ms-2">Optional: one AI call puts this in words. Every number and name is checked against the plan.</span>
    </template>
    <div v-if="error && !explanation" class="notice notice-warn mt-2" role="status"><span class="glyph" aria-hidden="true">!</span><span>{{ error.display }}</span></div>

    <details v-if="explanation" class="small mt-2" data-testid="ai-diagnostics"><summary>AI details</summary>
      <p class="mb-1 mt-1" data-testid="ai-outcome"><strong>{{ outcome.label }}.</strong> A model call was {{ outcome.attempted ? 'made' : 'not made' }}; its wording was {{ outcome.state === 'accepted' ? 'accepted' : 'not used' }}.</p>
      <ul v-if="rejected.length" class="mb-1" data-testid="ai-rejected"><li v-for="r in rejected" :key="r">{{ r }}</li></ul>
      <p v-if="explanation.dropped" class="mb-1" data-testid="cite-dropped">{{ explanation.dropped }} sentence(s) were left out because code could not tie them to the facts.</p>
      <details v-if="explanation.facts?.length" class="mb-1"><summary>Facts the sentences rest on</summary><ul class="mb-0 mt-1" data-testid="cite-facts"><li v-for="f in explanation.facts" :key="f.id"><strong>{{ f.id }}:</strong> {{ costTerms(f.text) }}</li></ul></details>
      <AiDrawer kind="explain" :result="explanation" class="mb-1" />
    </details>
  </section>
  <section v-else class="card-soft" :aria-labelledby="headingId" data-testid="explain-block">
    <h2 :id="headingId" class="h6 d-flex flex-wrap align-items-center gap-2">{{ title }} <AiMark v-if="explanation?.source === 'llm'" kind="ai" label="AI-written" /><AiMark v-else-if="explanation" kind="calc" label="Template" />
      <span v-if="explanation" class="badge-src" :class="badge.kind === 'llm' ? 'badge-verified' : 'badge-sample'" data-testid="explain-badge">{{ badge.label }}</span></h2>
    <div v-if="store.aiOff && !explanation" class="notice notice-info" role="status" data-testid="explain-ai-off"><span class="glyph" aria-hidden="true">i</span><span>AI off. {{ WOULD_ADD.explain }}</span></div>
    <button v-else-if="!explanation" type="button" class="btn btn-primary" :disabled="busy || disabled" @click="emit('explain')" data-testid="explain-button">
      {{ busy ? 'Writing the explanation…' : title }}</button>
    <p v-if="!explanation && !store.aiOff" class="small muted mt-2 mb-0">One click, one AI call. If the AI is off, you get a template summary. Warnings from the planner are always added by code.</p>
    <div v-if="error && !explanation" class="notice notice-warn mt-2" role="status"><span class="glyph" aria-hidden="true">!</span><span>{{ error.display }}</span></div>
    <template v-if="explanation">
      <div v-if="explanation.cited" class="mt-2 mb-2" data-testid="explain-cited">
        <p class="mb-1" data-testid="explain-text"><template v-for="(s, i) in explanation.sentences" :key="i"><span>{{ costTerms(s.text) }}</span>
          <button v-for="id in s.fact_ids" :key="id" type="button" class="cite-chip" :data-testid="`cite-${id}`" :aria-label="`Source ${id}: ${costTerms(factText[id])}`" :aria-describedby="active === id ? citeId : undefined"
            @mouseenter="show(id)" @mouseleave="hide" @focus="show(id)" @blur="hide" @keydown.esc="hide">{{ id }}</button>{{ ' ' }}</template></p>
        <p :id="citeId" class="small mb-1" role="status" aria-live="polite" data-testid="cite-source"><template v-if="active"><strong>{{ active }}:</strong> {{ costTerms(factText[active]) }}</template><template v-else>Each sentence names the facts it rests on (F1, F2, ...). Hover or focus a chip to see the fact and where its number is in the tables.</template></p>
        <details class="small"><summary>The facts the sentences rest on</summary><ul class="mb-0 mt-1" data-testid="cite-facts"><li v-for="f in explanation.facts" :key="f.id"><strong>{{ f.id }}:</strong> {{ costTerms(f.text) }}</li></ul></details>
        <p v-if="explanation.dropped" class="small muted mb-0" data-testid="cite-dropped">{{ explanation.dropped }} sentence(s) written by the AI were left out because code could not tie them to the facts.</p>
      </div>
      <p v-else class="mt-2 mb-2" style="white-space: pre-line" data-testid="explain-text">{{ costTerms(explanation.text) }}</p>
      <div v-if="explanation.warnings?.length" class="notice notice-warn mb-2" role="note" data-testid="explain-warnings">
        <span class="glyph" aria-hidden="true">!</span>
        <div><strong>Warnings from the planner</strong><ul class="mb-0"><li v-for="w in explanation.warnings" :key="w">{{ costTerms(w) }}</li></ul></div>
      </div>
      <p class="small muted mb-1">Supporting text only; the tables are the source of truth.</p>
      <AiDrawer kind="explain" :result="explanation" class="mb-2" />
      <details class="small"><summary>How was this checked?</summary>
        <p class="mb-0 mt-1">The AI gets only this result's computed numbers and names, never place descriptions. Every number, time and name in its text is compared with them; on any mismatch its text is discarded and a template summary is shown.</p></details>
    </template>
  </section>
</template>
