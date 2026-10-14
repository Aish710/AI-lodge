<script setup>
// Create trip: free text -> POST /parse -> a PROPOSAL that fills the EDITABLE form below. Nothing is submitted by this panel.
import { computed, ref } from 'vue'
import NameResolution from './NameResolution.vue'
import ErrorPanel from './ErrorPanel.vue'
import SwitchOffer from './SwitchOffer.vue'
import CurrencyConfirm from './CurrencyConfirm.vue'
import { store, runParse, chooseName, rateLimited, maxInputChars } from '../store.js'
import { originOf, parseState } from '../lib/rules.js'
import { titleCase } from '../lib/format.js'

const text = ref('')
const over = computed(() => text.value.length > maxInputChars)
const state = computed(() => parseState(store.parseResult, store.health?.llm_limit_reached === true))
const r = computed(() => store.parseResult)
const json = computed(() => (r.value?.extracted_json ? JSON.stringify(r.value.extracted_json, null, 2) : null))
const LABELS = { fx: 'Exchange rate', budget_scope: 'What the budget covers', budget_interpreted: 'Budget as understood', value_of_time_interpreted: 'Value of time as understood' }
const assumptions = computed(() => Object.entries(r.value?.assumptions ?? {}).filter(([k]) => k !== 'fx_jpy_per_sgd').map(([k, v]) => [LABELS[k] ?? titleCase(k), String(v)]))
const placed = ref([])
function pick({ input, id, name }) {
  chooseName(id, originOf(input, r.value?.extracted_json) === 'skip' ? 'skip' : 'must')
  placed.value.push(`${name} was added to your sights as ${originOf(input, r.value?.extracted_json) === 'skip' ? '"Not interested"' : '"Must visit"'}.`)
}
const unresolved = computed(() => (r.value?.unresolved_names ?? []).filter((u) => !placed.value.some((p) => p.includes(u.input))))
</script>
<template>
  <section class="card-soft" aria-labelledby="nl-h" data-testid="nl-panel">
    <h2 id="nl-h" class="h5">Describe your trip in words <span class="muted fw-normal">(optional)</span></h2>
    <p class="small muted">The AI assistant only proposes values for the form below. You review and edit everything. Your text is cleaned before it is sent; place descriptions are never sent.</p>
    <label class="form-label" for="nl-text">For example: "3 days, about 20,000 yen, I must see Senso-ji, relaxed pace"</label>
    <textarea id="nl-text" class="form-control" rows="3" v-model="text" :aria-invalid="over" aria-describedby="nl-count"></textarea>
    <div class="d-flex flex-wrap justify-content-between align-items-center mt-2 gap-2">
      <div id="nl-count" class="small" :class="over ? 'text-danger fw-bold' : 'muted'" aria-live="polite" data-testid="nl-count">{{ text.length }} / {{ maxInputChars }} characters<span v-if="over"> — too long: shorten it (nothing is cut off for you)</span></div>
      <button type="button" class="btn btn-outline-primary" :disabled="!text.trim() || over || store.busy.parse || rateLimited" @click="runParse(text)" data-testid="nl-extract">{{ store.busy.parse ? 'Reading…' : 'Extract' }}</button>
    </div>

    <ErrorPanel v-if="store.parseError" :error="store.parseError" class="mt-3" />

    <div v-if="state.kind === 'unavailable' || state.kind === 'limit'" class="notice notice-info mt-3" role="status" :data-testid="state.kind === 'limit' ? 'nl-limit' : 'nl-unavailable'">
      <span class="glyph" aria-hidden="true">i</span><span>{{ state.message }}</span>
    </div>

    <div v-if="state.kind === 'ok' || state.kind === 'clarify'" class="mt-3 stack" aria-live="polite" data-testid="nl-result">
      <div class="notice notice-good"><span class="glyph" aria-hidden="true">✓</span><span>
        <template v-if="state.kind === 'ok'">The form below has been filled in from this draft. Review and edit it before you continue.</template>
        <template v-else>The assistant needs more information. {{ r.draft ? 'What it understood is in the form below; please check it.' : 'Nothing was filled in.' }}</template></span></div>
      <div v-if="r.clarifications.length" class="notice notice-warn" role="note" data-testid="nl-clarifications"><span class="glyph" aria-hidden="true">?</span><ul class="mb-0"><li v-for="c in r.clarifications" :key="c">{{ c }}</li></ul></div>
      <SwitchOffer :offer="r.switch_offer" />
      <CurrencyConfirm :items="r.currency_confirmations ?? []" />
      <div class="row g-3">
        <div class="col-12 col-md-5"><h3 class="h6">What you wrote</h3><div class="json-box" data-testid="nl-raw">{{ r.raw_input_echo }}</div></div>
        <div class="col-12 col-md-7"><h3 class="h6">What the assistant extracted (before checking)</h3><pre class="json-box mb-0" data-testid="nl-json">{{ json ?? 'nothing extracted' }}</pre></div>
      </div>
      <div v-if="r.defaults_applied.length" data-testid="nl-defaults"><h3 class="h6">Defaults filled in (you did not say)</h3><ul class="mb-0 small"><li v-for="d in r.defaults_applied" :key="d">{{ d }}</li></ul></div>
      <div v-if="assumptions.length" data-testid="nl-assumptions"><h3 class="h6">Assumptions</h3><ul class="mb-0 small"><li v-for="[k, v] in assumptions" :key="k"><strong>{{ k }}:</strong> {{ v }}</li></ul></div>
      <div v-if="r.unclear.length" data-testid="nl-unclear"><h3 class="h6">The assistant was unsure about</h3><ul class="mb-0 small"><li v-for="u in r.unclear" :key="u">{{ u }}</li></ul></div>
      <NameResolution :unresolved="unresolved" :ambiguities="r.ambiguities" @pick="pick" />
      <ul v-if="placed.length" class="small mb-0" aria-live="polite"><li v-for="p in placed" :key="p">{{ p }}</li></ul>
    </div>
  </section>
</template>
