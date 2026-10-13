<script setup>
// REAL errors only ({error:{code,message,details}}): network, timeout, 4xx validation, 5xx. An infeasible trip is NOT an error: see ConflictPanel.
defineProps({ error: { type: Object, required: true }, retryable: Boolean })
defineEmits(['retry'])
</script>
<template>
  <div class="notice notice-error" role="alert" data-testid="error-panel">
    <span class="glyph" aria-hidden="true">✕</span>
    <div>
      <strong>Something went wrong.</strong>
      <div>{{ error.display ?? error.message }}</div>
      <div class="small mt-1">Code: <code>{{ error.code }}</code><span v-if="error.status"> · HTTP {{ error.status }}</span></div>
      <button v-if="retryable" class="btn btn-sm btn-outline-secondary mt-2" @click="$emit('retry')">Try again</button>
    </div>
  </div>
</template>
