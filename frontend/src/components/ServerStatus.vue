<script setup>
import { store, boot } from '../store.js'
</script>
<template>
  <div v-if="store.server === 'checking' || store.server === 'waking'" class="notice notice-info" role="status" aria-live="polite" data-testid="cold-start">
    <span class="spinner" aria-hidden="true"></span>
    <span v-if="store.server === 'waking'"><strong>Waking the server, this can take about a minute.</strong> The free host sleeps when idle. This is normal, nothing is wrong; the page will carry on by itself.</span>
    <span v-else>Connecting to the server…</span>
  </div>
  <div v-else-if="store.server === 'down'" class="notice notice-error" role="alert" data-testid="server-down">
    <span class="glyph" aria-hidden="true">✕</span>
    <span><strong>The server did not wake up in time.</strong> {{ store.serverError?.message }}
      <button class="btn btn-sm btn-outline-secondary ms-2" @click="boot()">Try again</button></span>
  </div>
</template>
