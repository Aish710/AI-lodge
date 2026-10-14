<script setup>
import { computed } from 'vue'
import { store } from '../store.js'
import Hint from './Hint.vue'
const place = computed(() => store.city?.display_name ?? 'Sample cities')
const code = computed(() => store.city?.currency_code ?? '')
</script>
<template>
  <div class="honesty honesty-slim" role="note" data-testid="honesty-banner">
    <div class="page py-1 d-flex gap-2 align-items-center">
      <strong aria-hidden="true">i</strong>
      <span><strong>Sample data</strong> · {{ place }}<template v-if="code"> · {{ code }}</template> · prices are examples</span>
      <Hint text="All places, prices, hours and travel times are samples or estimates. Hotels are made-up examples. Not live quotes." label="About the sample data" />
    </div>
  </div>
</template>
