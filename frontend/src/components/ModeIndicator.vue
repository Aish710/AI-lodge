<script setup>
import { computed } from 'vue'
import { store } from '../store.js'
const view = computed(() => {
  const h = store.health
  if (!h) return null
  if (h.llm_limit_reached) return { glyph: '!', cls: 'notice-warn', text: 'Sample mode (AI unavailable): the daily AI limit has been reached and resets later. Everything else works.' }
  if (h.mode === 'llm') return { glyph: '✓', cls: 'notice-good', text: 'AI assistant on' }
  return { glyph: 'i', cls: 'notice-info', text: 'Sample mode (AI unavailable)' }
})
</script>
<template>
  <div v-if="view" class="notice py-1 px-2" :class="view.cls" role="status" data-testid="mode-indicator" style="display:inline-flex">
    <span class="glyph" aria-hidden="true">{{ view.glyph }}</span><span>{{ view.text }}</span>
  </div>
</template>
