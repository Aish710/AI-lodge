<script setup>
// The independent validator's checks. A failing check is shown as a failure with text AND an icon, never as OK, and the panel is
// open by default whenever anything is not "pass".
import { computed } from 'vue'
import { checkIcon, checkLabel, overallLabel } from '../lib/rules.js'
import { topWarnings } from '../lib/band.js'
// compact: the unverified items are already listed once under "To check before you go", so the validator's own wording of them is folded into the details instead of repeated
const props = defineProps({ report: { type: Object, required: true }, compact: Boolean })
// in compact mode only the warnings "To check before you go" already lists (unknown prices or hours, advance booking) are folded away; every other warning stays visible
const covered = (w) => /unknown|advance booking|price/i.test(w)
const shownWarnings = computed(() => (props.compact ? (props.report.data_quality_warnings ?? []).filter((w) => !covered(w)) : props.report.data_quality_warnings ?? []))
const foldedWarnings = computed(() => (props.compact ? (props.report.data_quality_warnings ?? []).filter(covered) : []))
const warnings = computed(() => topWarnings(shownWarnings.value))
const failed = computed(() => props.report.checks.filter((c) => c.status === 'fail'))
// With no plan there is ONE check that only restates the summary: show the summary once and keep the check under "Technical details".
const noPlan = computed(() => props.report.verification === 'none' || (props.report.checks.length === 1 && props.report.checks[0].id === 'plan_exists'))
</script>
<template>
  <section class="card-soft" data-testid="feasibility-report" aria-labelledby="fr-h">
    <h2 id="fr-h" class="h5 d-flex flex-wrap align-items-center gap-2">
      Trip Feasibility Report
      <span class="pill" :class="{ 'pill-must': report.overall === 'fail' }" data-testid="overall">
        <span aria-hidden="true">{{ report.overall === 'fail' ? '✕' : report.overall === 'pass' ? '✓' : '!' }}</span> {{ overallLabel(report.overall) }}
      </span>
    </h2>
    <p class="mb-2" data-testid="report-summary">{{ report.summary }}</p>
    <ul v-if="failed.length && !noPlan" class="list-unstyled mb-2" data-testid="failed-checks">
      <li v-for="c in failed" :key="c.id" class="text-danger fw-semibold"><span aria-hidden="true">✕</span> Fail: {{ c.name }}. {{ c.message }}</li>
    </ul>
    <p v-if="report.verification === 'conditional'" class="small mb-2" data-testid="report-conditional"><strong>Conditional, not fully verified.</strong> Feasible only if the sights marked "Opening hours unverified" are open at their scheduled time. Check before you travel.</p>
    <details :open="report.overall !== 'pass' && !noPlan">
      <summary class="fw-semibold">{{ noPlan ? 'Technical details' : `All ${report.checks.length} checks` }}</summary>
      <ul class="list-unstyled mt-2 mb-0">
        <li v-for="c in report.checks" :key="c.id" class="d-flex gap-2 py-1" :data-status="c.status" data-testid="check">
          <span class="fw-bold flex-none" style="width:5.5em" :class="{ 'text-danger': c.status === 'fail' }">
            <span aria-hidden="true">{{ checkIcon(c.status) }}</span> {{ checkLabel(c.status) }}
          </span>
          <span><strong>{{ c.name }}.</strong> {{ c.message }}</span>
        </li>
      </ul>
      <template v-if="foldedWarnings.length"><h3 class="h6 mt-2" data-testid="dq-warnings-folded">Validator wording of items listed under "To check before you go"</h3><ul class="mb-0"><li v-for="w in foldedWarnings" :key="w">{{ w }}</li></ul></template>
    </details>
    <div v-if="shownWarnings.length" class="mt-3" data-testid="dq-warnings">
      <h3 class="h6">Data-quality warnings</h3>
      <ul class="mb-0"><li v-for="w in warnings.shown" :key="w">{{ w }}</li></ul>
      <details v-if="warnings.more.length" class="mt-1"><summary>Show {{ warnings.more.length }} more</summary><ul class="mb-0 mt-1"><li v-for="w in warnings.more" :key="w">{{ w }}</li></ul></details>
    </div>
  </section>
</template>
