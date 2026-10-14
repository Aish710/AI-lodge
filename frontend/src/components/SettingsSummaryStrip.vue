<script setup>
import { computed } from 'vue'
import { store } from '../store.js'
import { tripSummaryText } from '../lib/tripSummary.js'

const summary = computed(() => tripSummaryText(store))
</script>

<template>
  <section class="settings-strip" aria-label="Trip settings summary" data-testid="settings-strip">
    <span>{{ summary }}</span>
    <router-link to="/" data-testid="edit-trip-settings">Edit trip settings</router-link>
  </section>
</template>
