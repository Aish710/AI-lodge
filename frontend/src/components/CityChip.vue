<script setup>
// The selected city is always visible: name, country and currency. It is read from the single store value, never from a prop.
import { computed } from 'vue'
import Icon from './Icon.vue'
import { store } from '../store.js'
const city = computed(() => store.city)
</script>
<template>
  <span v-if="city" class="city-chip" data-testid="city-chip" :title="`This trip covers ${city.display_name}, ${city.country}. Amounts are in ${city.currency_code}.`">
    <Icon name="pin" :size="16" />
    <strong>{{ city.display_name }}</strong><span class="city-chip-rest"> · {{ city.currency_code }}</span>
  </span>
</template>
