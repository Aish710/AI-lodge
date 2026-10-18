<script setup>
// "What the AI did": raw model output beside the validated result, what code rejected or changed and why, the number of AI calls, and which parts code did.
import { computed, ref } from 'vue'
import { drawerModel } from '../lib/aiDrawer.js'
import { store } from '../store.js'
import AiMark from './AiMark.vue'
const props = defineProps({ kind: { type: String, required: true }, result: { type: Object, default: null } })
const m = computed(() => drawerModel(props.kind, props.result, { health: store.health }))
// The body is rendered only while the drawer is open, so nothing technical (such as a rejection) shows up in the page unless asked for.
const open = ref(false)
const rawText = computed(() => (m.value?.raw ? JSON.stringify(m.value.raw, null, 2) : null))
</script>
<template>
  <details v-if="m" class="ai-drawer small" :data-testid="`ai-drawer-${kind}`" @toggle="open = $event.target.open">
    <summary class="fw-semibold">What the AI did</summary>
    <div v-if="open" class="mt-2 stack">
      <p class="mb-0" data-testid="drawer-source"><AiMark :kind="m.llm ? 'ai' : 'calc'" :label="m.llm ? 'AI wording accepted' : m.attempted ? 'AI tried, not used' : 'No AI call'" /> {{ m.source }}. AI calls: <strong data-testid="drawer-calls">{{ m.calls }}</strong>.
        <template v-if="m.model"> Model: <strong>{{ m.model }}</strong><template v-if="m.host"> via {{ m.host }}</template>.</template>
        <template v-if="m.promptVersion"> Prompt version {{ m.promptVersion }}.</template></p>
      <div v-if="rawText" class="row g-2">
        <div class="col-12 col-md-6"><h4 class="h6">Raw model output (before checking)</h4><pre class="json-box mb-0" data-testid="drawer-raw">{{ rawText }}</pre></div>
        <div class="col-12 col-md-6"><h4 class="h6">What code did with it</h4>
          <ul class="mb-0" data-testid="drawer-changes"><li v-for="c in m.changes" :key="c.what"><strong>{{ c.what }}.</strong> {{ c.why }}</li><li v-if="!m.changes.length">Nothing was rejected or changed.</li></ul></div>
      </div>
      <div v-else><h4 class="h6">What code rejected or changed</h4>
        <ul class="mb-0" data-testid="drawer-changes"><li v-for="c in m.changes" :key="c.what"><strong>{{ c.what }}.</strong> {{ c.why }}</li><li v-if="!m.changes.length">Nothing was rejected or changed.</li></ul></div>
      <div><h4 class="h6">Parts done by code, not the AI</h4><ul class="mb-0" data-testid="drawer-code"><li v-for="c in m.codeDid" :key="c">{{ c }}</li></ul></div>
      <p class="muted mb-0">The drawer shows the model's structured answer and the checks around it. It never shows the system prompt, place descriptions or any key.</p>
    </div>
  </details>
</template>
