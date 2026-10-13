<script setup>
defineProps({ text: { type: String, default: 'Working…' } })
</script>
<template>
  <div class="notice notice-info" role="status" aria-live="polite" data-testid="loading"><span class="spinner" aria-hidden="true"></span><span>{{ text }}</span></div>
</template>
