<script setup>
// Provenance badge. Missing or unknown provenance is shown as "unknown", never hidden.
import { computed } from 'vue'
const props = defineProps({ status: { type: String, default: null }, what: { type: String, default: '' } })
const kind = computed(() => (props.status && ['sample', 'estimated', 'verified'].includes(props.status) ? props.status : 'unknown'))
</script>
<template>
  <span class="badge-src" :class="`badge-${kind}`" :title="`${what ? what + ': ' : ''}${kind} data`">
    <span class="sr-only">{{ what }} source: </span>{{ kind }}
  </span>
</template>
