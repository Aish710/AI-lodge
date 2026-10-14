<script setup>
import { computed } from 'vue'
import { store } from '../store.js'
const place = computed(() => store.city?.display_name ?? 'Sample cities')
</script>
<template>
  <div class="honesty" role="note" data-testid="honesty-banner">
    <div class="page py-2 d-flex gap-2 align-items-start">
      <strong aria-hidden="true">i</strong>
      <span><strong>Sample data:</strong> {{ place }} only, fictional hotels, estimated prices and travel times. Not live quotes.</span>
    </div>
  </div>
</template>
