<script setup>
defineProps({ lines: { type: Number, default: 4 }, height: { type: String, default: '1rem' } })
</script>
<template>
  <div class="card-soft" aria-hidden="true" data-testid="skeleton">
    <div v-for="n in lines" :key="n" class="skeleton mb-2" :style="{ height, width: n === lines ? '60%' : '100%' }"></div>
  </div>
</template>
