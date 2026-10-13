<script setup>
import { rateLimited, rateLimitSeconds } from '../store.js'
</script>
<template>
  <div v-if="rateLimited" class="notice notice-warn" role="status" aria-live="polite" data-testid="rate-limit">
    <span class="glyph" aria-hidden="true">!</span>
    <span><strong>Too many requests.</strong> Buttons that call the server are paused. You can try again in <strong data-testid="countdown">{{ rateLimitSeconds }}</strong> s.</span>
  </div>
</template>
