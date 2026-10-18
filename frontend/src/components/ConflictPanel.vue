<script setup>
// Decision 4: HTTP 200 + status "infeasible" is a NORMAL result. Specific conflicts in plain language, plus the server-computed
// alternatives as actions that re-run the request with that one change. Deliberately not the error style.
import { computed } from 'vue'
import { conflictActions } from '../lib/rules.js'
const props = defineProps({ result: { type: Object, required: true }, prefs: { type: Object, required: true }, placesById: { type: Object, required: true }, busy: Boolean, disabled: Boolean })
const emit = defineEmits(['apply'])
const actions = computed(() => conflictActions(props.result, props.prefs, props.placesById))
const name = (id) => props.placesById[id]?.name ?? id
</script>
<template>
  <section class="notice notice-info" aria-labelledby="conflict-h" data-testid="conflict-panel">
    <span class="glyph" aria-hidden="true">i</span>
    <div class="w-100">
      <h2 id="conflict-h" class="h5 mb-1">No plan satisfies every requirement</h2>
      <p class="mb-2">This is a result, not a fault: the planner checked and these requests cannot all be met together. Nothing was faked or dropped silently.</p>
      <ul class="mb-3" data-testid="conflict-list">
        <li v-for="(c, i) in result.conflicts" :key="i">
          {{ c.message }}
          <span v-if="c.attraction_ids?.length && c.attraction_ids.length < 4" class="muted"> ({{ c.attraction_ids.map(name).join(', ') }})</span>
          <code class="ms-1 small">{{ c.code }}</code>
        </li>
      </ul>
      <div v-if="actions.length">
        <h3 class="h6">What could work</h3>
        <p class="small muted mb-2" data-testid="alt-note">Each option below was actually solved and then re-checked by the independent validator. Nothing changes until you press a button. Options are ordered by how little they change; that is a convenience, not a proof that nothing smaller exists.</p>
        <ul class="list-unstyled mb-0 stack" data-testid="alternatives">
          <li v-for="a in actions" :key="a.kind + a.message">
            <button v-if="a.patch" class="btn btn-sm btn-primary" :disabled="busy || disabled" @click="emit('apply', a.patch)" :data-kind="a.kind">{{ a.label }}</button>
            <span v-if="a.patch && a.combination" class="pill ms-2" data-testid="alt-combo">two changes together</span>
            <span v-if="a.patch && a.verified" class="small muted ms-2">checked by the validator</span>
            <span v-else>{{ a.label }} <span class="muted">(change this in the form)</span></span>
          </li>
        </ul>
      </div>
      <p v-else class="mb-0" data-testid="no-repair">No verified repair was found, even trying pairs of changes within a fixed limit. The requirements cannot be met under the sample data and planning assumptions as entered; try changing the inputs yourself.</p>
    </div>
  </section>
</template>
