<script setup>
// Describe your travel style in words. The AI only TAGS supported preferences; code turns them into settings, labelled "you said it" (explicit) or "suggested" (inferred, needs your tick).
// Nothing is applied until you press Apply, and the plan is re-optimised only when you press "Plan my trip". A value you set yourself is kept unless you ask for it here.
import { computed, nextTick, ref, watch } from 'vue'
import { store, runStyleText, discardStyleProposal, applyStyleSettings, rateLimited, maxInputChars } from '../store.js'
import AiMark from './AiMark.vue'

const text = ref('')
const s = computed(() => store.styleAi)
const p = computed(() => store.styleAi.proposal)
const over = computed(() => text.value.length > maxInputChars)
const key = (x) => x.field + (x.target ?? '')
const picked = ref([])
const show = (v) => (v === null || v === undefined || v === '' ? 'not set' : v)
function ask() { picked.value = []; runStyleText(text.value).then(() => { picked.value = (store.styleAi.proposal?.settings ?? []).filter((x) => !x.kept_yours).map(key) }) }
watch(p, async (v) => { if (v) { await nextTick(); document.getElementById('sa-prev')?.focus() } })
function toggle(k, on) { const set = new Set(picked.value); on ? set.add(k) : set.delete(k); picked.value = [...set] }
function apply() { applyStyleSettings([...picked.value]); text.value = '' }
const chips = ['I prefer a slow trip with lots of breaks.', "I don't mind paying more if it saves time.", 'I want to see as many attractions as possible.', 'I want a relaxed trip without long travel periods.']
</script>
<template>
  <div class="mt-2" data-testid="style-assistant">
    <div class="small fw-semibold d-flex align-items-center gap-2">Or describe your style in words <AiMark kind="ai" /></div>
    <div v-if="store.aiOff" class="small muted" data-testid="style-ai-off">AI off: choose a style above or set the values yourself.</div>
    <template v-else>
      <div class="d-flex flex-wrap gap-2 my-1" role="group" aria-label="Examples (they fill the box and send nothing)"><button v-for="(c, i) in chips" :key="c" type="button" class="chip" :data-testid="'style-chip-' + i" @click="text = c">{{ c }}</button></div>
      <label class="visually-hidden" for="sa-text">Describe how you like to travel</label>
      <textarea id="sa-text" class="form-control form-control-sm" rows="2" v-model="text" :aria-invalid="over" data-testid="style-text"></textarea>
      <div class="d-flex flex-wrap align-items-center gap-2 mt-1"><button type="button" class="btn btn-outline-primary btn-sm" :disabled="!text.trim() || over || s.busy || rateLimited" data-testid="style-ask" @click="ask">{{ s.busy ? 'Reading…' : 'Suggest settings' }}</button>
        <span class="small muted">The AI only suggests; you choose what to apply.</span></div>
      <div v-if="s.error" class="notice notice-warn mt-2" role="alert"><span class="glyph" aria-hidden="true">!</span><span>{{ s.error.message }}</span></div>
      <div v-if="p" class="mt-2" aria-live="polite" data-testid="style-proposal">
        <div v-if="p.status === 'llm_unavailable'" class="small" data-testid="style-unavailable">{{ p.clarifications[0] }}</div>
        <template v-else>
          <strong id="sa-prev" class="small" tabindex="-1">Preview: nothing has changed yet</strong>
          <ul class="list-unstyled mb-1" data-testid="style-settings">
            <li v-for="x in p.settings" :key="key(x)" class="border rounded bg-white p-2 mb-1" :data-testid="'style-setting-' + x.field">
              <div class="form-check"><input :id="'sa-' + key(x)" class="form-check-input" type="checkbox" :checked="picked.includes(key(x))" @change="toggle(key(x), $event.target.checked)" />
                <label class="form-check-label" :for="'sa-' + key(x)"><strong>{{ x.label }}</strong>: {{ show(x.current) }} → <strong>{{ x.field === 'must_visit' ? 'required' : x.proposed }}</strong></label></div>
              <div class="small"><span class="pill" :data-testid="'source-' + x.field">{{ x.source === 'explicit' ? 'You said this' : 'Suggested by the AI (inferred)' }}</span>
                <span v-if="x.kept_yours" class="pill ms-1">You set this yourself: kept unless you tick it</span></div>
              <div class="small muted">{{ x.reason }}</div>
            </li>
          </ul>
          <ul v-if="p.questions.length" class="small" data-testid="style-questions"><li v-for="q in p.questions" :key="q">{{ q }}</li></ul>
          <ul v-if="p.unsupported.length" class="small" data-testid="style-unsupported"><li v-for="u in p.unsupported" :key="u">The planner cannot enforce: {{ u }}</li></ul>
          <ul v-if="p.clarifications.length" class="small"><li v-for="c in p.clarifications" :key="c">{{ c }}</li></ul>
          <div class="d-flex flex-wrap gap-2"><button type="button" class="btn btn-primary btn-sm" :disabled="!picked.length" data-testid="style-apply" @click="apply">Apply the ticked settings</button>
            <button type="button" class="btn btn-outline-secondary btn-sm" data-testid="style-cancel" @click="discardStyleProposal">Cancel</button></div>
          <p class="small muted mt-1 mb-0">Applying only changes the form. Press "Plan my trip" to re-optimise.</p>
        </template>
      </div>
    </template>
  </div>
</template>
