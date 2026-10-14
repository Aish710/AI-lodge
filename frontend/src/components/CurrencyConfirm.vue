<script setup>
// An amount the assistant could not safely read (for example "¥" or "$"): it is never guessed, so the user restates it in the form.
defineProps({ items: { type: Array, default: () => [] } })
</script>
<template>
  <div v-if="items.length" class="notice notice-warn" role="note" data-testid="currency-confirm">
    <span class="glyph" aria-hidden="true">?</span>
    <span>
      <strong>Please confirm the currency.</strong>
      <ul class="mb-0 small"><li v-for="c in items" :key="c.field + c.symbol">{{ c.message }}</li></ul>
    </span>
  </div>
</template>
