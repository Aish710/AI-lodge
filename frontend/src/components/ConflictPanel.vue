<script setup>
// HTTP 200 + status "infeasible" is a NORMAL result. Friendly explanations first (title, why, what to do), the server's technical sentences and codes in an expandable section.
// "Blocked by missing information" is kept apart from "no plan under the known constraints": missing data is never presented as a real-world impossibility.
// Every repair shows the exact change, why it may help, whether it was solved AND validated, and its effect. Nothing is applied until its button is pressed.
import { computed } from 'vue'
import { conflictActions } from '../lib/rules.js'
import { describeConflicts, headline, repairViews, resultState } from '../lib/conflicts.js'
import { formatLocalMoney } from '../lib/format.js'
import { store } from '../store.js'
const props = defineProps({ result: { type: Object, required: true }, prefs: { type: Object, required: true }, placesById: { type: Object, required: true }, busy: Boolean, disabled: Boolean })
const emit = defineEmits(['apply'])
const money = (v) => formatLocalMoney(v, store.city?.currency_code ?? 'JPY')
const mins = (m) => (m >= 60 ? `${Math.floor(m / 60)} h ${Math.round(m % 60)} min` : `${Math.round(m)} min`)
const state = computed(() => resultState({ result: props.result }))
const head = computed(() => headline(state.value) ?? headline('infeasible'))
const described = computed(() => describeConflicts(props.result.conflicts, props.placesById))
const actions = computed(() => conflictActions(props.result, props.prefs, props.placesById))
// pair each view with the action produced from the SAME alternative (same index in the server list)
const paired = computed(() => (props.result.alternatives ?? []).map((alt, i) => ({ view: repairViews({ alternatives: [alt] }, props.placesById, money, mins)[0], action: actions.value[i] })).filter((p) => p.view))
const name = (id) => props.placesById[id]?.name ?? id
</script>
<template>
  <section class="notice notice-info" aria-labelledby="conflict-h" data-testid="conflict-panel" :data-state="state">
    <span class="glyph" aria-hidden="true">i</span>
    <div class="w-100">
      <h2 id="conflict-h" class="h5 mb-1" data-testid="conflict-title">{{ head.title }}</h2>
      <p class="mb-2">{{ head.lead }}</p>
      <ul class="mb-3" data-testid="conflict-friendly">
        <li v-for="(c, i) in described" :key="i"><strong>{{ c.title }}.</strong> {{ c.body }}</li>
      </ul>
      <div>
        <h3 class="h6">Next steps</h3>
        <template v-if="paired.length">
          <p class="small muted mb-2" data-testid="alt-note">Each option below was actually solved and then re-checked by the independent validator. Nothing changes until you press its button. Options are ordered by how little they change; that is a convenience, not a proof that nothing smaller exists.</p>
          <ul class="list-unstyled mb-0 stack" data-testid="alternatives">
            <li v-for="p in paired" :key="p.view.key" class="border rounded bg-white p-2" :data-testid="'repair-' + p.view.kind">
              <div class="fw-semibold" data-testid="repair-title">{{ p.view.title }}<span v-if="p.view.combination" class="pill ms-2" data-testid="alt-combo">two changes together</span></div>
              <div v-if="p.view.why" class="small" data-testid="repair-why">Why it may help: {{ p.view.why }}</div>
              <div v-if="p.view.effect" class="small" data-testid="repair-effect">Resulting plan: {{ p.view.effect }}</div>
              <div class="small" :class="p.view.removesMust ? 'text-danger' : 'muted'" v-if="p.view.removesMust" data-testid="repair-warning">This gives up something you required.</div>
              <div class="d-flex flex-wrap align-items-center gap-2 mt-1">
                <button v-if="p.action?.patch" class="btn btn-sm btn-primary" :disabled="busy || disabled" :data-kind="p.view.kind" @click="emit('apply', p.action.patch)">Apply this change</button>
                <span v-else class="small muted">Change this in the form.</span>
                <span v-if="p.view.verified" class="pill" data-testid="repair-verified">Solved and checked by the validator</span>
                <span v-else class="pill" data-testid="repair-unverified">Not verified</span>
              </div>
            </li>
          </ul>
        </template>
        <p v-else class="mb-0" data-testid="no-repair">No verified repair was found, even trying pairs of changes within a fixed limit. Under the sample data and planning assumptions as entered there is no plan to confirm; try changing the inputs yourself.</p>
      </div>
      <details class="mt-3 small" data-testid="technical-details">
        <summary>Technical details</summary>
        <ul class="mb-0 mt-1" data-testid="conflict-list">
          <li v-for="(c, i) in result.conflicts" :key="i">{{ c.message }}
            <span v-if="c.attraction_ids?.length && c.attraction_ids.length < 4" class="muted"> ({{ c.attraction_ids.map(name).join(', ') }})</span>
            <code class="ms-1">{{ c.code }}</code></li>
        </ul>
      </details>
    </div>
  </section>
</template>
