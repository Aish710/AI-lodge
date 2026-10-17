<script setup>
// Itinerary: free text -> POST /parse-replan -> PROPOSED operations. Nothing runs: the user ticks what to keep and queues it; the queue is
// applied separately. A proposal cannot confirm a must-visit removal (the flag is only ever set by the dialog).
import { computed, ref, watch } from 'vue'
import NameResolution from './NameResolution.vue'
import ErrorPanel from './ErrorPanel.vue'
import SwitchOffer from './SwitchOffer.vue'
import CurrencyConfirm from './CurrencyConfirm.vue'
import AiMark from './AiMark.vue'
import { store, runProposal, discardProposal, queueProposal, rateLimited, maxInputChars } from '../store.js'
import { parseState } from '../lib/rules.js'

const text = ref('')
const over = computed(() => text.value.length > maxInputChars)
const p = computed(() => store.proposal)
const state = computed(() => parseState(p.value, store.health?.llm_limit_reached === true))
const include = ref([])
watch(p, (v) => { include.value = (v?.operations ?? []).map((_, i) => i) }, { immediate: true })
const canQueue = computed(() => p.value?.status === 'ok' && include.value.length > 0)
function pick({ input, name }) { text.value = text.value.replace(input, name) }
const added = ref(0)
function queue() { added.value = include.value.length; queueProposal([...include.value]); text.value = '' }
function toTray() { const el = document.getElementById('pending-h'); el?.scrollIntoView({ block: 'start' }); el?.setAttribute('tabindex', '-1'); el?.focus({ preventScroll: true }) }
// Example chips are built from THE CURRENT PLAN and only fill the box. Nothing is sent until "Ask the AI".
const chips = computed(() => {
  const stops = (store.plan?.result?.days ?? []).flatMap((d) => d.stops ?? []).filter((a) => a.attraction_id)
  const nm = (a) => store.placesById[a.attraction_id]?.name
  const first = stops[0], optional = stops.find((a) => !a.is_must_visit)
  return [first && nm(first) && `Move ${nm(first)} to the morning`, optional && nm(optional) && `Skip ${nm(optional)}`].filter(Boolean)
})
</script>
<template>
  <section class="card-soft" aria-labelledby="pr-h" data-testid="proposal-panel">
    <h2 id="pr-h" class="h5 d-flex flex-wrap align-items-center gap-2">Ask the AI to change your plan <AiMark kind="ai" /></h2>
    <p class="small muted">The AI turns your words into a <strong>proposal</strong>. You tick what you want and add it to your changes; nothing runs until you press Apply.</p>
    <div v-if="chips.length" class="d-flex flex-wrap gap-2 align-items-center mb-2" role="group" aria-label="Example changes (they fill the box and send nothing)" data-testid="replan-chips">
      <span class="small fw-semibold">Try:</span>
      <button v-for="(c, i) in chips" :key="c" type="button" class="chip" :data-testid="`replan-chip-${i}`" @click="text = c">{{ c }}</button>
    </div>
    <label class="form-label" for="pr-text">For example: "move Senso-ji to the morning of day 2" or "drop Shibuya Sky"</label>
    <textarea id="pr-text" class="form-control" rows="2" v-model="text" :aria-invalid="over" aria-describedby="pr-count"></textarea>
    <div class="d-flex flex-wrap justify-content-between align-items-center mt-2 gap-2">
      <div id="pr-count" class="small" :class="over ? 'text-danger fw-bold' : 'muted'" aria-live="polite">{{ text.length }} / {{ maxInputChars }} characters<span v-if="over"> — too long: shorten it</span></div>
      <button type="button" class="btn btn-outline-primary" :disabled="!text.trim() || over || store.busy.proposal || rateLimited" @click="runProposal(text)" data-testid="proposal-button">{{ store.busy.proposal ? 'Reading…' : 'Ask the AI' }}</button>
    </div>
    <div v-if="added && !p" class="notice notice-good mt-3" role="status" data-testid="proposal-added"><span class="glyph" aria-hidden="true">✓</span><span>Added {{ added }} change(s) to your pending changes. Nothing has been applied yet. <button type="button" class="btn btn-link btn-sm p-0 align-baseline" @click="toTray">Review and apply</button></span></div>
    <p v-else-if="store.queue.length && !p" class="small mt-2 mb-0" data-testid="proposal-pending-pointer">{{ store.queue.length }} pending change(s). <button type="button" class="btn btn-link btn-sm p-0 align-baseline" @click="toTray">Review and apply</button></p>
    <ErrorPanel v-if="store.proposalError" :error="store.proposalError" class="mt-3" />
    <div v-if="state.kind === 'unavailable' || state.kind === 'limit'" class="notice notice-info mt-3" role="status" data-testid="proposal-unavailable">
      <span class="glyph" aria-hidden="true">i</span><span>{{ state.message }} The buttons on each stop still work.</span></div>

    <div v-if="p && (state.kind === 'ok' || state.kind === 'clarify')" class="mt-3 stack" aria-live="polite" data-testid="proposal-card">
      <div class="notice notice-info"><span class="glyph" aria-hidden="true">i</span><span><strong>Proposal only.</strong> Nothing has been applied. {{ p.status === 'ok' ? 'Untick anything you do not want, then add the rest to your changes.' : 'It needs clarification first.' }}</span></div>
      <div v-if="p.requires_confirmation" class="notice notice-warn" data-testid="proposal-needs-confirmation">
        <span class="glyph" aria-hidden="true">!</span>
        <div><strong>This would remove a must-visit.</strong> You will be asked to confirm before anything is sent. The AI cannot confirm this for you.
          <ul class="mb-0"><li v-for="r in p.confirmation_reasons" :key="r">{{ r }}</li></ul></div></div>
      <ul v-if="p.operations.length" class="list-unstyled mb-0" data-testid="proposal-ops">
        <li v-for="(d, i) in p.descriptions" :key="i" class="form-check">
          <input :id="`pr-op-${i}`" class="form-check-input" type="checkbox" :value="i" v-model="include" :disabled="p.status !== 'ok'" />
          <label class="form-check-label" :for="`pr-op-${i}`">{{ d }}</label>
        </li>
      </ul>
      <p v-else class="mb-0">No operations were proposed.</p>
      <SwitchOffer :offer="p.switch_offer" />
      <CurrencyConfirm :items="p.currency_confirmations ?? []" />
      <div v-if="p.clarifications.length" class="notice notice-warn" data-testid="proposal-clarifications"><span class="glyph" aria-hidden="true">?</span><ul class="mb-0"><li v-for="c in p.clarifications" :key="c">{{ c }}</li></ul></div>
      <div v-if="p.unclear.length" class="small"><strong>The assistant was unsure about:</strong> {{ p.unclear.join('; ') }}</div>
      <NameResolution :unresolved="p.unresolved_names" :ambiguities="p.ambiguities" @pick="pick" />
      <p v-if="p.unresolved_names.length || p.ambiguities.length" class="small muted mb-0">Choosing a name puts it into your text above. Press "Propose changes" again to see the updated proposal.</p>
      <div class="d-flex gap-2">
        <button type="button" class="btn btn-primary" :disabled="!canQueue" @click="queue" data-testid="proposal-queue">Add to my changes</button>
        <button type="button" class="btn btn-outline-secondary" @click="discardProposal" data-testid="proposal-discard">Discard</button>
      </div>
    </div>
  </section>
</template>
