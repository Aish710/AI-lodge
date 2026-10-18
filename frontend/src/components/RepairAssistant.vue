<script setup>
// AI-assisted repair, inside the conflict panel. The AI turns words into a PROPOSAL from a fixed list of actions; the server tries it on a copy with the normal optimiser and the
// independent validator. Nothing changes until the person presses Apply, and every change that gives something up needs its own tick. If the AI is off or fails, the repair cards above still work.
import { computed, nextTick, ref, watch } from 'vue'
import { store, runRepair, cancelRepair, applyRepair, repairApplicable, toggleRepairConfirm, rateLimited, solverBusy, maxInputChars } from '../store.js'
import AiMark from './AiMark.vue'

const text = ref(store.repair.text)
const r = computed(() => store.repair)
const p = computed(() => store.repair.proposal)
const over = computed(() => text.value.length > maxInputChars)
const names = computed(() => (store.planPrefs?.must_visit ?? []).map((id) => store.placesById[id]?.name).filter(Boolean))
const chips = computed(() => [
  names.value.length >= 1 && `I really want to visit ${names.value.slice(0, 2).join(' and ')}. What can I change?`,
  'Keep my hotel, but make the schedule work.',
  'Remove optional attractions before touching my must-visits.',
  'I can finish one hour later if necessary.',
].filter(Boolean))
const state = computed(() => p.value?.verification?.state ?? null)
const stateText = computed(() => ({ verified: 'Solved and checked by the independent validator: a plan exists with these changes.', conditional: 'Solved and checked, but provisional: the plan holds only if the sights marked "Opening hours unverified" are open.',
  infeasible: 'Not verified: no plan was found with these changes.', blocked_missing_info: 'Not verified: still blocked by missing information.' }[state.value] ?? 'Not verified.'))
const can = computed(() => repairApplicable(p.value, r.value.confirmed) && !solverBusy.value && !rateLimited.value && !r.value.applying)
const sourceOff = computed(() => store.aiOff)
function ask() { runRepair(text.value) }
// move keyboard and screen-reader focus to the proposal when it arrives, so the answer is announced and reachable without hunting for it
watch(p, async (v) => { if (v) { await nextTick(); document.getElementById('rp-h')?.focus({ preventScroll: false }) } })
function focusProposal() { document.getElementById('rp-h')?.focus() }
</script>
<template>
  <section class="mt-3 border-top pt-3" data-testid="repair-assistant" aria-labelledby="ra-h">
    <h3 id="ra-h" class="h6 d-flex flex-wrap align-items-center gap-2">Ask the AI to suggest a change <AiMark kind="ai" /></h3>
    <div v-if="sourceOff" class="notice notice-info" role="status" data-testid="repair-ai-off"><span class="glyph" aria-hidden="true">i</span><span>AI off: the repair options above work the same. Nothing is sent to a model.</span></div>
    <template v-else>
      <p class="small muted mb-2">Describe what you can live with. The AI proposes changes from a fixed list; the planner then checks them. <strong>Nothing is applied until you press Apply.</strong></p>
      <div class="d-flex flex-wrap gap-2 mb-2" role="group" aria-label="Example requests (they fill the box and send nothing)">
        <button v-for="(c, i) in chips" :key="c" type="button" class="chip" :data-testid="'repair-chip-' + i" @click="text = c">{{ c }}</button>
      </div>
      <label class="form-label small" for="ra-text">Your request</label>
      <textarea id="ra-text" class="form-control" rows="2" v-model="text" :aria-invalid="over" aria-describedby="ra-count" data-testid="repair-text"></textarea>
      <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mt-2">
        <div class="form-check mb-0"><input id="ra-keep" class="form-check-input" type="checkbox" v-model="r.keepHotel" data-testid="repair-keep-hotel" /><label class="form-check-label small" for="ra-keep">Keep my hotel (no hotel change)</label></div>
        <div id="ra-count" class="small" :class="over ? 'text-danger fw-bold' : 'muted'" aria-live="polite">{{ text.length }} / {{ maxInputChars }}</div>
        <button type="button" class="btn btn-outline-primary btn-sm" :disabled="!text.trim() || over || r.busy || r.applying || rateLimited || solverBusy" data-testid="repair-ask" @click="ask">{{ r.busy ? 'Reading your request…' : 'Ask the AI' }}</button>
      </div>
      <div v-if="r.error" class="notice notice-warn mt-2" role="alert" data-testid="repair-error"><span class="glyph" aria-hidden="true">!</span><span>{{ r.error.message }} <span v-if="r.error.code === 'stale_proposal'">Your plan is unchanged.</span></span></div>

      <div v-if="p" class="mt-3 stack" aria-live="polite" data-testid="repair-proposal">
        <h4 id="rp-h" class="h6 mb-0" tabindex="-1">Proposal only: nothing has been applied</h4>
        <div v-if="p.status === 'llm_unavailable'" class="notice notice-info" data-testid="repair-unavailable"><span class="glyph" aria-hidden="true">i</span><span>{{ p.clarifications[0] }} Your plan is unchanged.</span></div>
        <template v-else>
          <div data-testid="repair-understood"><strong>What the AI understood</strong>
            <ul class="mb-1"><li v-for="u in p.understood" :key="u">{{ u }}</li><li v-if="p.keep_hotel_inferred">You want to keep your hotel: no hotel change is proposed.</li></ul>
            <p v-if="!p.understood.length" class="small mb-1">No change could be proposed from that request.</p>
            <ul v-if="p.unsupported.length" class="small mb-1" data-testid="repair-unsupported"><li v-for="u in p.unsupported" :key="u">Not something the planner can do: {{ u }}</li></ul>
            <ul v-if="p.refused.length" class="small mb-1" data-testid="repair-refused"><li v-for="x in p.refused" :key="x.why">Not allowed: {{ x.why }}</li></ul>
            <ul v-if="p.clarifications.length" class="small mb-1" data-testid="repair-clarify"><li v-for="x in p.clarifications" :key="x">{{ x }}</li></ul>
          </div>
          <div v-if="p.actions.length">
            <strong>Proposed changes</strong>
            <ul class="list-unstyled mb-1" data-testid="repair-actions">
              <li v-for="a in p.actions" :key="a.id" class="border rounded bg-white p-2 mb-1" :data-testid="'repair-action-' + a.action">
                <div class="fw-semibold">{{ p.understood[p.actions.indexOf(a)] }}</div>
                <div v-if="a.reason" class="small muted">Why: {{ a.reason }}</div>
                <div class="small"><span v-if="a.hard_constraint" class="pill pill-must me-1">Changes a hard rule</span><span v-if="a.requires_confirmation" class="pill">Needs your confirmation</span></div>
                <div v-if="a.requires_confirmation" class="form-check mt-1"><input :id="'ra-c-' + a.id" class="form-check-input" type="checkbox" :checked="r.confirmed.includes(a.id)" :data-testid="'repair-confirm-' + a.id" @change="toggleRepairConfirm(a.id, $event.target.checked)" /><label class="form-check-label small" :for="'ra-c-' + a.id">I confirm this change</label></div>
              </li>
            </ul>
            <div v-if="p.unchanged.length" class="small" data-testid="repair-unchanged"><strong>Stays the same:</strong> {{ p.unchanged.join(' · ') }}</div>
            <div class="small mt-1" data-testid="repair-verification" :class="state === 'verified' || state === 'conditional' ? '' : 'text-danger'"><strong>Planner check:</strong> {{ stateText }}
              <span v-if="p.verification?.conflicts?.length" class="d-block muted">{{ p.verification.conflicts[0] }}</span></div>
          </div>
          <div class="d-flex flex-wrap gap-2">
            <button type="button" class="btn btn-primary btn-sm" :disabled="!can" data-testid="repair-apply" @click="applyRepair">{{ r.applying ? 'Applying…' : 'Apply these changes' }}</button>
            <button type="button" class="btn btn-outline-secondary btn-sm" data-testid="repair-cancel" @click="cancelRepair">Cancel</button>
            <button type="button" class="btn btn-outline-secondary btn-sm" :disabled="r.busy || !r.text" data-testid="repair-retry" @click="runRepair(r.text)">Ask again</button>
          </div>
          <p v-if="p.actions.some((a) => a.requires_confirmation) && !can" class="small muted mb-0">Tick each confirmation to enable Apply.</p>
        </template>
      </div>
    </template>
  </section>
</template>
