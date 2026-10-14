<script setup>
// The destination check (done in code on the server) found another city. This only OFFERS the switch: the user presses, then confirms.
import { requestCitySwitch } from '../store.js'
defineProps({ offer: { type: Object, default: null } })
</script>
<template>
  <div v-if="offer" class="notice notice-info" data-testid="switch-offer">
    <span class="glyph" aria-hidden="true">i</span>
    <span>
      <button type="button" class="btn btn-sm btn-primary me-2" @click="requestCitySwitch(offer.city_id)" data-testid="switch-offer-button">Switch to {{ offer.display_name }}</button>
      <span class="small">Nothing is switched for you. {{ offer.display_name }}, {{ offer.country }} will be selected only if you confirm.</span>
    </span>
  </div>
</template>
