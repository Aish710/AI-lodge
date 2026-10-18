<script setup>
// Always-visible undo for the last change: a plain swap back to the previous plan this session remembers (no recompute, nothing edited).
import { computed } from 'vue'
import { store, restoreState, solverBusy } from '../store.js'
const idx = computed(() => store.history.findIndex((h) => h.plan === store.plan && h.kind === 'accepted'))
const back = computed(() => (idx.value < 0 ? null : store.history.slice(idx.value + 1).find((h) => h.kind === 'accepted') ?? null))
const label = computed(() => store.history[idx.value]?.label ?? 'last change')
</script>
<template>
  <div v-if="back || store.restored" class="notice notice-info d-flex flex-wrap align-items-center gap-2" role="status" data-testid="undo-bar">
    <span v-if="store.restored" data-testid="undo-done">Previous plan restored. Nothing was edited.</span>
    <template v-if="back">
      <span>Last change: <strong>{{ label }}</strong>.</span>
      <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="solverBusy" data-testid="undo-last" @click="restoreState(back.id)">Undo (back to “{{ back.label }}”)</button>
    </template>
  </div>
</template>
