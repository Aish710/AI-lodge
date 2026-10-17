<script setup>
// Unresolved names and ambiguities from the natural-language paths. Suggestions are NEVER auto-accepted: each needs a click.
defineProps({ unresolved: { type: Array, default: () => [] }, ambiguities: { type: Array, default: () => [] } })
const emit = defineEmits(['pick'])
</script>
<template>
  <div v-if="unresolved.length || ambiguities.length" class="stack" data-testid="name-resolution">
    <div v-for="u in unresolved" :key="u.input" class="notice notice-warn" data-testid="unresolved">
      <span class="glyph" aria-hidden="true">?</span>
      <div><strong>"{{ u.input }}"</strong>: {{ u.message }}
        <div v-if="u.suggestions?.length" class="mt-1">Did you mean:
          <button v-for="s in u.suggestions" :key="s.id" type="button" class="chip ms-1" @click="emit('pick', { input: u.input, id: s.id, name: s.name })" data-testid="suggestion-chip">{{ s.name }}</button>
        </div>
        <div v-else class="small mt-1">No close match: not in this city's data, so it cannot be added.</div></div>
    </div>
    <div v-for="a in ambiguities" :key="a.input" class="notice notice-info" data-testid="ambiguity">
      <span class="glyph" aria-hidden="true">?</span>
      <div><strong>"{{ a.input }}"</strong> could mean more than one place. Pick one:
        <button v-for="c in a.candidates" :key="c.id" type="button" class="chip ms-1" @click="emit('pick', { input: a.input, id: c.id, name: c.name })" data-testid="candidate-chip">{{ c.name }}</button></div>
    </div>
  </div>
</template>
