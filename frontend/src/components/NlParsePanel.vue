<script setup>
// Create trip: free text -> POST /parse -> a PROPOSAL that fills the EDITABLE form below. Nothing is submitted by this panel.
import { computed, ref } from 'vue'
import NameResolution from './NameResolution.vue'
import ErrorPanel from './ErrorPanel.vue'
import SwitchOffer from './SwitchOffer.vue'
import Hint from './Hint.vue'
import ModeIndicator from './ModeIndicator.vue'
import CurrencyConfirm from './CurrencyConfirm.vue'
import AiMark from './AiMark.vue'
import AiLegend from './AiLegend.vue'
import aiExamples from '../lib/aiExamples.json'
import { assumedList, understoodRows } from '../lib/understood.js'
import { store, runParse, chooseName, rateLimited, maxInputChars, applyParseToForm, cancelParse } from '../store.js'
import { originOf, parseState } from '../lib/rules.js'
import { titleCase } from '../lib/format.js'

const text = ref('')
const over = computed(() => text.value.length > maxInputChars)
const state = computed(() => parseState(store.parseResult, store.health?.llm_limit_reached === true))
const r = computed(() => store.parseResult)
// Shown before any click, so a visitor knows the AI box is switched off rather than broken.
const aiOffNote = computed(() => {
  const h = store.health
  if (!h || h.mode === 'llm' && !h.llm_limit_reached) return null
  return h.llm_limit_reached ? 'The daily AI limit has been reached; the form works the same.' : 'AI is off in this deployment; the form works the same.'
})
const json = computed(() => (r.value?.extracted_json ? JSON.stringify(r.value.extracted_json, null, 2) : null))
const LABELS = { fx: 'Exchange rate', budget_scope: 'What the budget covers', budget_interpreted: 'Budget as understood', value_of_time_interpreted: 'Value of time as understood' }
const assumptions = computed(() => Object.entries(r.value?.assumptions ?? {}).filter(([k]) => k !== 'fx_jpy_per_sgd').map(([k, v]) => [LABELS[k] ?? titleCase(k), String(v)]))
const placed = ref([])
function pick({ input, id, name }) {
  chooseName(id, originOf(input, r.value?.extracted_json) === 'skip' ? 'skip' : 'must')
  placed.value.push(`${name} was added to your sights as ${originOf(input, r.value?.extracted_json) === 'skip' ? '"Not interested"' : '"Must visit"'}.`)
}
const cityExamples = computed(() => aiExamples[store.cityId] ?? null)
const EXAMPLES = [['typical', 'A typical request', 'ex-typical'], ['wrong_city', 'Try a wrong-city request', 'ex-wrong-city'], ['vague_place', 'Try a vague place', 'ex-vague']]
// Example prompts only FILL the box. Nothing is sent until "Ask the AI" is clicked.
function fill(kind) { text.value = cityExamples.value?.[kind] ?? ''; document.getElementById('nl-text')?.focus() }
const rows = computed(() => understoodRows(r.value, { places: store.places ?? [], currency: store.city?.currency_code }))
const assumed = computed(() => assumedList(r.value?.defaults_applied ?? []))
const applied = ref(false)
function apply() { applied.value = applyParseToForm(); document.getElementById('f-days')?.focus() }
function changeField(id) { const el = document.getElementById(id); el?.closest('details')?.setAttribute('open', ''); el?.focus() }
const unresolved = computed(() => (r.value?.unresolved_names ?? []).filter((u) => !placed.value.some((p) => p.includes(u.input))))
</script>
<template>
  <section class="card-soft ai-card" aria-labelledby="nl-h" data-testid="nl-panel">
    <h2 id="nl-h" class="h4 d-flex flex-wrap align-items-center gap-2">Ask the AI to set up your trip <AiMark kind="ai" /></h2>
    <p class="mb-1">The AI fills the form below. You check everything before anything is planned. <Hint text="Your text is cleaned before it is sent. Place descriptions are never sent." /></p>
    <AiLegend class="mb-2" />
    <div v-if="aiOffNote" class="d-flex flex-wrap gap-2 align-items-center mb-2" data-testid="ai-off-note">
      <ModeIndicator testid="ai-box-mode" />
      <span class="small">{{ aiOffNote }}</span>
    </div>
    <div v-if="cityExamples" class="d-flex flex-wrap gap-2 align-items-center mb-2" role="group" aria-label="Example requests (they fill the box and send nothing)" data-testid="ai-examples">
      <span class="small fw-semibold">Try:</span>
      <button v-for="[kind, label, tid] in EXAMPLES" :key="kind" type="button" class="chip example-prompt" :data-testid="tid" @click="fill(kind)" :title="cityExamples[kind]">{{ label }}</button>
    </div>
    <label class="form-label" for="nl-text">For example: "3 days, about 20,000 yen, I must see Senso-ji, relaxed pace"</label>
    <textarea id="nl-text" class="form-control" rows="3" v-model="text" :aria-invalid="over" aria-describedby="nl-count"></textarea>
    <div class="d-flex flex-wrap justify-content-between align-items-center mt-2 gap-2">
      <div id="nl-count" class="small" :class="over ? 'text-danger fw-bold' : 'muted'" aria-live="polite" data-testid="nl-count">{{ text.length }} / {{ maxInputChars }} characters<span v-if="over"> — too long: shorten it (nothing is cut off for you)</span></div>
      <div class="d-flex gap-2">
        <button v-if="store.busy.parse" type="button" class="btn btn-outline-secondary" @click="cancelParse" data-testid="nl-cancel">Cancel</button>
        <button type="button" class="btn btn-primary" :disabled="!text.trim() || over || store.busy.parse || rateLimited" @click="runParse(text); applied = false" data-testid="nl-extract">{{ store.busy.parse ? 'Reading…' : 'Ask the AI' }}</button>
      </div>
    </div>

    <ErrorPanel v-if="store.parseError" :error="store.parseError" retryable class="mt-3" @retry="runParse(text)" />

    <div v-if="state.kind === 'unavailable' || state.kind === 'limit'" class="notice notice-info mt-3" role="status" :data-testid="state.kind === 'limit' ? 'nl-limit' : 'nl-unavailable'">
      <span class="glyph" aria-hidden="true">i</span><span>{{ state.message }}</span>
    </div>

    <div v-if="state.kind === 'ok' || state.kind === 'clarify'" class="mt-3 stack" aria-live="polite" data-testid="nl-result">
      <h3 class="h5 mb-0" id="understood-h">What the AI understood</h3>
      <div class="notice notice-good"><span class="glyph" aria-hidden="true">✓</span><span>
        <template v-if="state.kind === 'ok'">The form below has been filled in from this draft. Review and edit it before you continue.</template>
        <template v-else>The assistant needs more information. {{ r.draft ? 'What it understood is in the form below; please check it.' : 'Nothing was filled in.' }}</template></span></div>
      <div v-if="r.clarifications.length" class="notice notice-warn" role="note" data-testid="nl-clarifications"><span class="glyph" aria-hidden="true">?</span><ul class="mb-0"><li v-for="c in r.clarifications" :key="c">{{ c }}</li></ul></div>
      <SwitchOffer :offer="r.switch_offer" />
      <CurrencyConfirm :items="r.currency_confirmations ?? []" />
      <div class="understood-grid">
        <div><h4 class="h6">What you wrote</h4><div class="json-box" data-testid="nl-raw">{{ r.raw_input_echo }}</div></div>
        <div v-if="rows.length" data-testid="nl-rows"><h4 class="h6">What the AI set <AiMark kind="ai" label="AI read" /></h4>
          <ul class="understood-rows"><li v-for="row in rows" :key="row.field" :data-testid="`row-${row.field}`"><strong>{{ row.label }}:</strong> <span>{{ row.value }}</span> <AiMark kind="ai" label="AI read" /></li></ul></div>
      </div>
      <div v-if="assumed.length" data-testid="nl-defaults"><h4 class="h6">I assumed (you did not say)</h4>
        <ul class="mb-0 small"><li v-for="d in assumed" :key="d.text">{{ d.text }} <AiMark kind="calc" label="Default" />
          <button v-if="d.field" type="button" class="btn btn-link btn-sm p-0 ms-1 align-baseline" @click="changeField(d.field)">Change</button></li></ul></div>
      <div v-if="assumptions.length" data-testid="nl-assumptions"><h4 class="h6">Assumptions</h4><ul class="mb-0 small"><li v-for="[k, v] in assumptions" :key="k"><strong>{{ k }}:</strong> {{ v }}</li></ul></div>
      <div v-if="r.unclear.length" data-testid="nl-unclear"><h4 class="h6">The assistant was unsure about</h4><ul class="mb-0 small"><li v-for="u in r.unclear" :key="u">{{ u }}</li></ul></div>
      <p v-if="r.ambiguities.length || unresolved.length" class="small mb-0" data-testid="nl-optional-note">Optional: pick a place below if you want it in your trip. "Apply to my trip" does not wait for this.</p>
      <NameResolution :unresolved="unresolved" :ambiguities="r.ambiguities" @pick="pick" />
      <ul v-if="placed.length" class="small mb-0" aria-live="polite"><li v-for="p in placed" :key="p">{{ p }}</li></ul>
      <details class="small" data-testid="nl-raw-json"><summary>What the assistant extracted (before checking)</summary><pre class="json-box mb-0 mt-1" data-testid="nl-json">{{ json ?? 'nothing extracted' }}</pre></details>
      <div v-if="r.draft" class="d-flex flex-wrap align-items-center gap-2">
        <button type="button" class="btn btn-outline-primary" @click="apply" data-testid="nl-apply">Apply to my trip</button>
        <span class="small" role="status" data-testid="nl-applied">{{ applied ? 'Form filled in below. Nothing has been planned yet.' : 'The form below is already filled in from this reading. Nothing is planned until you click "Plan my trip". Apply again after editing to restore it.' }}</span>
      </div>
    </div>
  </section>
</template>
