<script setup>
// The independent validator's checks. A failing check is shown as a failure with text AND an icon, never as OK, and the panel is
// open by default whenever anything is not "pass".
import { checkIcon, checkLabel, overallLabel } from '../lib/rules.js'
defineProps({ report: { type: Object, required: true } })
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
    <details :open="report.overall !== 'pass'">
      <summary class="fw-semibold">All {{ report.checks.length }} checks</summary>
      <ul class="list-unstyled mt-2 mb-0">
        <li v-for="c in report.checks" :key="c.id" class="d-flex gap-2 py-1" :data-status="c.status" data-testid="check">
          <span class="fw-bold flex-none" style="width:5.5em" :class="{ 'text-danger': c.status === 'fail' }">
            <span aria-hidden="true">{{ checkIcon(c.status) }}</span> {{ checkLabel(c.status) }}
          </span>
          <span><strong>{{ c.name }}.</strong> {{ c.message }}</span>
        </li>
      </ul>
    </details>
    <div v-if="report.data_quality_warnings?.length" class="mt-3" data-testid="dq-warnings">
      <h3 class="h6">Data-quality warnings</h3>
      <ul class="mb-0"><li v-for="w in report.data_quality_warnings" :key="w">{{ w }}</li></ul>
    </div>
  </section>
</template>
