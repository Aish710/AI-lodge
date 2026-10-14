<script setup>
// The selected city is always visible: name, country and currency. It is read from the single store value, never from a prop.
import { computed } from 'vue'
import { store } from '../store.js'
const city = computed(() => store.city)
</script>
<template>
  <span v-if="city" class="city-chip" data-testid="city-chip" :title="`This trip covers ${city.display_name}, ${city.country}. Amounts are in ${city.currency_code}.`">
    <span aria-hidden="true">📍</span>
    <strong>{{ city.display_name }}</strong><span class="city-chip-rest"> · {{ city.country }} · {{ city.currency_code }}</span>
  </span>
</template>
