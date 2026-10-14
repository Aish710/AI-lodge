<script setup>
// Status is always icon + word + colour, never colour alone.
defineProps({ kind: { type: String, default: 'good' }, icon: { type: String, default: '✓' }, label: { type: String, required: true } })
</script>
<template><span class="status-chip" :class="`status-${kind}`" data-testid="status-chip"><span aria-hidden="true">{{ icon }}</span> {{ label }}</span></template>
