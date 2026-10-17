<script setup>
// The header chip. When the AI is on it is a BUTTON that opens what the AI does and never does, and where it runs.
import { computed, ref, useId } from 'vue'
import { store } from '../store.js'
const props = defineProps({ testid: { type: String, default: 'mode-indicator' } })
const open = ref(false)
const popId = `mode-pop-${useId()}`
const view = computed(() => {
  const h = store.health
  if (!h) return null
  if (h.llm_limit_reached) return { glyph: '!', cls: 'notice-warn', text: 'Sample mode (AI unavailable): the daily AI limit has been reached and resets later. Everything else works.', on: false }
  if (h.mode === 'llm') return { glyph: '✓', cls: 'notice-good', text: 'AI assistant on', on: true }
  return { glyph: 'i', cls: 'notice-info', text: 'Sample mode (AI unavailable)', on: false }
})
const host = computed(() => store.health?.llm_endpoint ?? null)
function onKey(e) { if (e.key === 'Escape') open.value = false }
</script>
<template>
  <div v-if="view" class="mode-wrap" @keydown="onKey">
    <div class="notice py-1 px-2" :class="view.cls" role="status" :data-testid="props.testid" style="display:inline-flex">
      <span class="glyph" aria-hidden="true">{{ view.glyph }}</span>
      <button type="button" class="mode-btn" :aria-expanded="open" :aria-controls="popId" @click="open = !open" data-testid="ai-popover-button">{{ view.text }} <span aria-hidden="true">▾</span></button>
    </div>
    <div v-if="open && view.on" :id="popId" class="mode-pop" role="region" aria-label="What the AI does here" data-testid="ai-popover">
      <div class="row g-3">
        <div class="col-12 col-sm-6"><h3 class="h6">What the AI does here</h3>
          <ul class="small mb-0 ps-3"><li>Reads your words and fills the form for you to check</li><li>Asks you when it is unsure</li><li>Writes short explanations of results</li></ul></div>
        <div class="col-12 col-sm-6"><h3 class="h6">What it never does</h3>
          <ul class="small mb-0 ps-3"><li>Pick your schedule (the optimiser does)</li><li>Invent prices, hours or times</li><li>Change your plan without your click</li></ul></div>
      </div>
      <p class="small fw-semibold mt-2 mb-1">Every AI answer is checked by code before you see it.</p>
      <p class="small muted mb-2" data-testid="ai-popover-where">Runs only when you click. <template v-if="host">Requests go through the gateway <strong>{{ host }}</strong> (a third party).</template></p>
      <button type="button" class="btn btn-outline-secondary btn-sm" @click="open = false">Close</button>
    </div>
    <div v-else-if="open" :id="popId" class="mode-pop" role="region" aria-label="AI is off" data-testid="ai-popover"><p class="small mb-2"><strong>AI off:</strong> the form works the same.</p><button type="button" class="btn btn-outline-secondary btn-sm" @click="open = false">Close</button></div>
  </div>
</template>
