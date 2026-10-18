<script setup>
import { costTerms } from '../lib/costTerms.js'
// Before / after / delta for an APPLIED replan. Everything comes from the server's diff; nothing is computed here except the direction cue.
// A saving next to a "Not like-for-like" warning always carries that warning beside the number.
import { computed } from 'vue'
import FeasibilityReport from './FeasibilityReport.vue'
import { diffRows, trueCostCaveat } from '../lib/replan.js'
import { minutesToHm } from '../lib/format.js'
import { money } from '../lib/money.js'
const props = defineProps({ result: { type: Object, required: true }, placesById: { type: Object, default: () => ({}) } })
const diff = computed(() => props.result.diff)
const rows = computed(() => diffRows(diff.value))
const caveat = computed(() => trueCostCaveat(diff.value))
const show = (r, v) => (r.unit === 'min' ? minutesToHm(v) : money(v))
const signed = (r) => (r.delta === 0 ? '0' : `${r.delta > 0 ? '+' : '−'}${r.unit === 'min' ? minutesToHm(Math.abs(r.delta)) : money(Math.abs(r.delta))}`)
const dayTime = (day, start) => `day ${day}, ${start}`
</script>
<template>
  <section class="card-soft" aria-labelledby="diff-h" data-testid="diff-view">
    <h2 id="diff-h" class="h5">What changed</h2>
    <p class="mb-2" data-testid="diff-summary">{{ costTerms(result.summary) }}</p>

    <div v-if="diff.warnings.length" class="notice notice-warn mb-3" role="note" data-testid="diff-warnings">
      <span class="glyph" aria-hidden="true">!</span>
      <div><strong>Read before trusting the numbers</strong>
        <ul class="mb-0 mt-1"><li v-for="w in diff.warnings" :key="w">{{ w }}</li></ul></div>
    </div>
    <div v-if="result.approximate" class="notice notice-warn mb-3" data-testid="diff-approximate"><span class="glyph" aria-hidden="true">!</span><span><strong>Approximate.</strong> The solver stopped at its time limit without proving this plan optimal.</span></div>

    <div class="table-responsive">
      <table class="table table-honest align-middle" data-testid="diff-table">
        <caption class="sr-only">Cost and travel lines before and after the change</caption>
        <thead><tr><th scope="col">Line</th><th scope="col" class="num">Before</th><th scope="col" class="num">After</th><th scope="col" class="num">Change</th></tr></thead>
        <tbody>
          <tr v-for="r in rows" :key="r.key" :class="{ 'fw-bold': r.strong }" :data-testid="`diff-${r.key}`">
            <th scope="row">{{ r.label }}</th>
            <td class="num">{{ show(r, r.before) }}</td>
            <td class="num">{{ show(r, r.after) }}</td>
            <td class="num" :class="`delta-${r.direction}`">
              <span aria-hidden="true">{{ r.glyph }}</span> {{ signed(r) }} <span class="sr-only">({{ r.word }})</span>
              <div v-if="r.key === 'true_cost_jpy' && caveat.show" class="small fw-normal" style="color: var(--amber)" data-testid="not-like-for-like">
                <span aria-hidden="true">!</span> Not like-for-like: {{ caveat.isSaving ? 'this saving' : 'this change' }} partly comes from a different set of sights, so it is not a pure saving.
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="row g-3">
      <div class="col-12 col-md-6"><h3 class="h6">Kept ({{ diff.kept.length }})</h3>
        <ul class="small" data-testid="diff-kept"><li v-for="a in diff.kept" :key="a.attraction_id">{{ a.name }} <span class="muted">({{ dayTime(a.day, a.start) }})</span></li><li v-if="!diff.kept.length" class="muted">None</li></ul></div>
      <div class="col-12 col-md-6"><h3 class="h6">Moved ({{ diff.moved.length }})</h3>
        <ul class="small" data-testid="diff-moved">
          <li v-for="m in diff.moved" :key="m.attraction_id">{{ m.name }}: {{ dayTime(m.from_day, m.from_start) }} → {{ dayTime(m.to_day, m.to_start) }}
            <span class="pill">{{ m.reason === 'user' ? 'by you' : 're-optimised' }}</span></li>
          <li v-if="!diff.moved.length" class="muted">None</li></ul></div>
      <div class="col-12 col-md-6"><h3 class="h6">Removed ({{ diff.removed.length }})</h3>
        <ul class="small" data-testid="diff-removed">
          <li v-for="a in diff.removed" :key="a.attraction_id">{{ a.name }} <span class="muted">(was {{ dayTime(a.day, a.start) }})</span>
            <span class="pill">{{ a.reason === 'removed_by_user' ? 'removed by you' : 'dropped by the planner' }}</span>
            <span v-if="a.was_must_visit" class="pill pill-must">was a must-visit</span></li>
          <li v-if="!diff.removed.length" class="muted">None</li></ul></div>
      <div class="col-12 col-md-6"><h3 class="h6">Added ({{ diff.added.length }})</h3>
        <ul class="small" data-testid="diff-added"><li v-for="a in diff.added" :key="a.attraction_id">{{ a.name }} <span class="muted">({{ dayTime(a.day, a.start) }})</span></li><li v-if="!diff.added.length" class="muted">None</li></ul></div>
    </div>

    <div class="mt-2" data-testid="diff-missed">
      <h3 class="h6">Optional sights left out</h3>
      <p class="small mb-1">Newly left out: <strong>{{ diff.newly_missed.length ? diff.newly_missed.join(', ') : 'none' }}</strong>. Back in the plan: <strong>{{ diff.no_longer_missed.length ? diff.no_longer_missed.join(', ') : 'none' }}</strong>.</p>
    </div>
    <p class="small mb-3" data-testid="diff-disruption">
      Disruption: <strong>{{ diff.disruption_count }}</strong> activities moved without you asking, at {{ money(diff.disruption_jpy_per_move) }} per move = {{ money(diff.disruption_cost_jpy) }}
      (informational, not part of the generalised cost). A shift of {{ diff.move_threshold_minutes }} minutes or less does not count.
    </p>
    <FeasibilityReport :report="result.feasibility_report" />
  </section>
</template>
