<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import NlParsePanel from '../components/NlParsePanel.vue'
import examples from '../lib/examples.json'
import { exampleLabel } from '../lib/rules.js'
import { store, currentPrefs, loadExample, requestCitySwitch, resetAll } from '../store.js'
import { nightsUsed } from '../lib/prefs.js'
import { budgetInJpy } from '../lib/prefs.js'
import { formatLocalMoney, WEEKDAY_NAMES, WEEKDAYS } from '../lib/format.js'
import { budgetSanityHint } from '../lib/tripSummary.js'
import Hint from '../components/Hint.vue'

const router = useRouter()
const errors = computed(() => currentPrefs().errors)
const city = computed(() => store.city)
const currencyOptions = computed(() => Array.from(new Set([city.value?.currency_code ?? 'JPY', city.value?.display_currency_code ?? 'SGD'])))
const budgetLocal = computed(() => budgetInJpy(store.form, city.value))
const budgetHint = computed(() => budgetSanityHint(store))
const vot = computed(() => Number(store.form.valueOfTime))
const exLabel = exampleLabel(examples.valid)
function next() { if (!errors.value.length) router.push('/wishlist') }
async function example(kind) { await loadExample(kind); router.push(kind === 'valid' ? '/hotels' : '/itinerary') }
function startOver() {
  if (!window.confirm('Clear this trip and start over?')) return
  resetAll()
  router.push('/')
}
const pickCity = requestCitySwitch
</script>
<template>
  <div class="stack">
    <div>
      <h1>Plan your trip</h1>
      <p class="muted mb-0">Pick the hotel and the plan together. <Hint text="A hotel that looks cheap can cost more once travel time and fares are counted." /></p>
    </div>

    <section class="card-soft" aria-labelledby="city-h">
      <h2 id="city-h" class="h5">Choose a city</h2>
      <p class="muted small mb-3">Sample data: verify before real travel.</p>
      <div class="row g-3">
        <template v-if="!store.cities.length"><div v-for="n in 4" :key="`sk${n}`" class="col-12 col-md-6 col-xl-3"><div class="city-card-skeleton skeleton" aria-hidden="true"></div></div></template>
        <div v-for="c in store.cities" :key="c.id" class="col-12 col-md-6 col-xl-3">
          <button type="button" class="city-card w-100 text-start" :class="{ active: c.id === store.cityId }" @click="pickCity(c.id)" :aria-pressed="c.id === store.cityId" :data-testid="`city-${c.id}`">
            <span class="city-name">{{ c.display_name }}</span>
            <span class="muted d-block">{{ c.country }}</span>
            <span class="badge-src badge-sample mt-2">sample data</span>
            <span class="d-block small mt-2">{{ c.currency_code }} · {{ c.counts.attractions }} sights · {{ c.counts.hotels }} demo hotels</span>
          </button>
        </div>
      </div>
      <p v-if="city" class="small mb-0 mt-3"><strong>Using {{ city.display_name }}.</strong> {{ city.sample_fx_label }}</p>
    </section>

    <div class="card-soft d-flex flex-wrap gap-2 align-items-center" data-testid="demo-helpers">
      <strong class="me-2">Quick demo:</strong>
      <button class="btn btn-outline-primary btn-sm" @click="example('valid')" data-testid="load-example" :title="exLabel.title" :aria-describedby="'ex-note'">{{ exLabel.text }}</button>
      <button class="btn btn-outline-secondary btn-sm" @click="example('impossible')" data-testid="load-impossible">Try an impossible trip</button>
      <p id="ex-note" class="small muted mb-0 w-100" data-testid="example-note"><strong>About this example:</strong> it values an hour at {{ exLabel.vot }} so the hotel trade-off shows. It is not typical: on random trips the cheapest hotel was usually the best. See the <router-link to="/proof#hotel-value">Proof page</router-link>.</p>
    </div>

    <NlParsePanel />

    <form class="card-soft" @submit.prevent="next" novalidate aria-label="Trip details">
      <fieldset class="form-group mb-3">
        <legend class="group-legend">When</legend>
        <div class="row g-3">
          <div class="col-6 col-md-3">
            <label class="form-label" for="f-days">Days</label>
            <input id="f-days" class="form-control" type="number" min="1" max="7" v-model.number="store.form.days" />
          </div>
          <div class="col-6 col-md-3">
            <label class="form-label" for="f-weekday">First day is a</label>
            <select id="f-weekday" class="form-select" v-model.number="store.form.startWeekday">
              <option v-for="(w, i) in WEEKDAYS" :key="w" :value="i">{{ WEEKDAY_NAMES[w] }}</option>
            </select>
          </div>
          <div class="col-6 col-md-3">
            <label class="form-label" for="f-start">Day starts</label>
            <input id="f-start" class="form-control" type="time" v-model="store.form.dayStart" />
          </div>
          <div class="col-6 col-md-3">
            <label class="form-label" for="f-end">Day ends</label>
            <input id="f-end" class="form-control" type="time" v-model="store.form.dayEnd" />
          </div>
        </div>
      </fieldset>

      <fieldset class="form-group mb-3">
        <legend class="group-legend">Money</legend>
        <div class="row g-3">
          <div class="col-12 col-md-6">
            <label class="form-label" for="f-budget">Budget for sights and transport (optional)</label>
            <div class="input-group">
              <input id="f-budget" class="form-control" type="number" min="0" inputmode="numeric" v-model="store.form.budgetAmount" aria-describedby="budget-help" />
              <select class="form-select" style="max-width:6.5rem" v-model="store.form.budgetCurrency" aria-label="Budget currency"><option v-for="cur in currencyOptions" :key="cur">{{ cur }}</option></select>
            </div>
            <div id="budget-help" class="form-text">
              Sights and transport only (no rooms or food).
              <span v-if="city" data-testid="fx-note">{{ city.sample_fx_label }}<span v-if="budgetLocal"> → {{ formatLocalMoney(budgetLocal, city.currency_code) }}</span>.</span>
            </div>
            <div v-if="budgetHint" class="form-text budget-hint" data-testid="budget-sanity-hint">{{ budgetHint }}</div>
            <div class="form-check form-switch mt-2">
              <input id="f-strict" class="form-check-input" type="checkbox" role="switch" v-model="store.form.strictBudget" :disabled="!store.form.budgetAmount && store.form.budgetAmount !== 0" />
              <label class="form-check-label" for="f-strict">Strict: never exceed it (otherwise a target)</label>
            </div>
          </div>
          <div class="col-12 col-md-6">
            <label class="form-label" for="f-vot">Value of an hour of your time <Hint text="Travel time is priced at this rate when hotels are compared by true cost." /> <strong data-testid="vot-value">{{ formatLocalMoney(vot, city?.currency_code ?? 'JPY') }} / hour</strong></label>
            <input id="f-vot" class="form-range" type="range" min="0" :max="city?.currency_code === 'KRW' ? 50000 : city?.currency_code === 'JPY' ? 5000 : 300" :step="city?.currency_code === 'KRW' ? 1000 : 1" v-model.number="store.form.valueOfTime" />
          </div>
        </div>
      </fieldset>

      <fieldset class="form-group mb-3">
        <legend class="group-legend">Style</legend>
        <label class="form-label" for="f-pace">Pace</label>
        <select id="f-pace" class="form-select" style="max-width:22rem" v-model="store.form.pace">
          <option value="relaxed">Relaxed (up to 2 sights a day)</option>
          <option value="balanced">Balanced (up to 3 a day)</option>
          <option value="packed">Packed (up to 4 a day)</option>
        </select>
      </fieldset>

      <details class="mb-2" data-testid="advanced">
        <summary class="fw-semibold">Advanced</summary>
        <div class="row g-3 mt-1">
          <div class="col-12 col-md-6">
            <div class="form-check">
              <input id="f-nights" class="form-check-input" type="checkbox" v-model="store.form.nightsOverride" />
              <label class="form-check-label" for="f-nights">Set the number of nights myself</label>
            </div>
            <input v-if="store.form.nightsOverride" id="f-nights-n" class="form-control mt-2" type="number" min="0" max="30" v-model.number="store.form.nights" aria-label="Number of nights" />
            <div class="form-text" data-testid="nights-used">Rooms are priced for <strong>{{ nightsUsed(store.form) }}</strong> night(s) {{ store.form.nightsOverride ? '(your setting)' : '(default: days − 1)' }}.</div>
          </div>
          <div class="col-12 col-md-6">
            <div class="form-check form-switch">
              <input id="f-unknown" class="form-check-input" type="checkbox" role="switch" v-model="store.form.allowUnknownHours" />
              <label class="form-check-label" for="f-unknown">Allow sights with unknown opening hours</label>
            </div>
            <div class="form-text">Off: unknown hours are never assumed open. On: such stops are scheduled but flagged.</div>
          </div>
        </div>
      </details>

      <div v-if="errors.length" class="notice notice-warn mt-3" role="alert" data-testid="form-errors">
        <span class="glyph" aria-hidden="true">!</span><ul class="mb-0 ps-3"><li v-for="e in errors" :key="e">{{ e }}</li></ul>
      </div>
      <div class="mt-3 d-flex flex-wrap gap-2 align-items-center">
        <button type="submit" class="btn btn-primary" :disabled="errors.length > 0" data-testid="next-wishlist">Next: choose sights</button>
        <button type="button" class="btn btn-outline-secondary" @click="startOver" data-testid="start-over">Start over</button>
      </div>
      <p class="small muted mb-0 mt-2" data-testid="state-retention-note">Your choices are kept while you move between steps. They are not saved if you refresh or close this page.</p>
    </form>
  </div>
</template>
