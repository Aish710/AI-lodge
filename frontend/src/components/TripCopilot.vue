<script setup>
import { computed, ref, watch } from 'vue'
import { askCopilot } from '../api/routes.js'
import { store, solverBusy, rateLimited, maxInputChars } from '../store.js'

const text = ref(''), reply = ref(null), error = ref(''), busy = ref(false)
let generation = 0
// Invalidate in-flight responses even when a newly solved plan has identical inputs.
watch(() => [store.plan, store.planPrefs, store.cityId, store.chosenHotel], () => { generation++; reply.value = null; error.value = ''; busy.value = false }, { deep: true })
const disabled = computed(() => busy.value || solverBusy.value || rateLimited.value)
const questions = [
  ['Why this plan?', 'EXPLAIN_PLAN'], ['Why expensive?', 'EXPLAIN_COST_BREAKDOWN'],
  ['Make it cheaper', 'ANALYSE_TRADEOFF'], ['Reduce travel', 'ANALYSE_TRADEOFF'],
  ['Keep my must-visits', 'EXPLAIN_CONSTRAINT'], ['Compare alternatives', 'COMPARE_ALTERNATIVES'],
  ['What is uncertain?', 'IDENTIFY_UNCERTAINTY'],
]
const targets = { scenario: ['whatif', 'Open What if?'], alternatives: ['explorer', 'Open Trade-off Explorer'], repair: ['copilot-repair', 'Open repair controls'] }
async function ask(operation = null) {
  if (disabled.value || !store.plan?.fingerprint || (!operation && (!text.value.trim() || text.value.length > maxInputChars))) return
  const token = ++generation
  busy.value = true; error.value = ''; reply.value = null
  try {
    const value = await askCopilot(store.planPrefs, store.plan.result, store.plan.fingerprint, text.value, operation, store.cityId)
    if (token === generation && value.fingerprint === store.plan?.fingerprint) reply.value = value
  } catch {
    if (token === generation) error.value = 'The question could not be checked. Your plan is unchanged. Try a quick question or use the controls below.'
  } finally { if (token === generation) busy.value = false }
}
function go() {
  const target = document.querySelector(`[data-testid="${targets[reply.value.handoff]?.[0]}"]`)
  target?.scrollIntoView({ behavior: 'smooth', block: 'start' }); target?.focus({ preventScroll: true })
}
const shown = value => Array.isArray(value) ? value.join(', ') || 'None listed' : typeof value === 'boolean' ? (value ? 'Yes' : 'No') : value
</script>
<template>
  <section class="card-soft" data-testid="trip-copilot" aria-labelledby="copilot-h">
    <h2 id="copilot-h" class="h5">Understand your trip</h2>
    <p class="small muted">Ask about this plan. Answers use checked plan evidence. Changes use the preview and Apply controls below.</p>
    <div class="d-flex flex-wrap gap-2 mb-2" aria-label="Quick questions">
      <button v-for="[label, operation] in questions" :key="label" class="btn btn-sm btn-outline-primary" :disabled="disabled" @click="ask(operation)">{{ label }}</button>
    </div>
    <p v-if="store.aiOff" class="small" data-testid="copilot-ai-off">AI off. Quick questions still work without a model.</p>
    <form v-else @submit.prevent="ask()">
      <label for="copilot-question" class="form-label small">Your question</label>
      <div class="d-flex gap-2"><input id="copilot-question" class="form-control" v-model="text" :maxlength="maxInputChars" placeholder="Why was an attraction omitted?" /><button class="btn btn-primary" :disabled="disabled || !text.trim()">Ask</button></div>
    </form>
    <p v-if="busy" role="status" class="small mt-2">Checking this plan…</p>
    <p v-if="error" role="alert" class="small mt-2">{{ error }}</p>
    <div v-if="reply" aria-live="polite" class="mt-3" data-testid="copilot-answer">
      <p>{{ reply.message }}</p>
      <p class="small muted">{{ reply.interpretation }} Nothing applied.</p>
      <dl class="small">
        <template v-for="e in reply.evidence" :key="e.reference">
          <dt>{{ e.label }} <span class="pill">{{ e.kind }}</span></dt>
          <dd>{{ shown(e.value) }} <span class="muted">({{ e.reference }})</span></dd>
        </template>
      </dl>
      <button v-if="targets[reply.handoff]" class="btn btn-sm btn-outline-primary" @click="go">{{ targets[reply.handoff][1] }}</button>
    </div>
  </section>
</template>
