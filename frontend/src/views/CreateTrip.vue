<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import NlParsePanel from '../components/NlParsePanel.vue'
import examples from '../lib/examples.json'
import { exampleLabel } from '../lib/rules.js'
import { store, currentPrefs, loadExample, selectCity } from '../store.js'
import { nightsUsed } from '../lib/prefs.js'
import { budgetInJpy } from '../lib/prefs.js'
import { formatLocalMoney, WEEKDAY_NAMES, WEEKDAYS } from '../lib/format.js'

const router = useRouter()
const errors = computed(() => currentPrefs().errors)
const city = computed(() => store.city)
const currencyOptions = computed(() => Array.from(new Set([city.value?.currency_code ?? 'JPY', city.value?.display_currency_code ?? 'SGD'])))
const budgetLocal = computed(() => budgetInJpy(store.form, city.value))
const vot = computed(() => Number(store.form.valueOfTime))
const exLabel = exampleLabel(examples.valid)
function next() { if (!errors.value.length) router.push('/wishlist') }
function example(kind) { loadExample(kind); router.push(kind === 'valid' ? '/hotels' : '/itinerary') }
async function pickCity(id) {
  if (id === store.cityId) return
  const hasWork = Object.keys(store.wishlist).length || store.chosenHotel || store.comparison || store.plan
  if (hasWork && !window.confirm('Changing city clears your wishlist, hotel choice, comparison and itinerary because the data is different. Continue?')) return
  await selectCity(id)
}
</script>
<template>
  <div class="stack">
    <div>
      <h1>Plan your trip</h1>
      <p class="muted mb-0">Choose the hotel and the itinerary together: a hotel that looks cheap can cost more once travel time and fares are counted.</p>
    </div>

    <section class="card-soft" aria-labelledby="city-h">
      <h2 id="city-h" class="h5">Choose a city</h2>
      <p class="muted small mb-3">All city packs are sample data. Prices, hours, exchange rates and fictional hotel rates must be verified before real travel.</p>
      <div class="row g-3">
        <div v-for="c in store.cities" :key="c.id" class="col-12 col-md-6 col-xl-3">
          <button type="button" class="city-card w-100 text-start" :class="{ active: c.id === store.cityId }" @click="pickCity(c.id)" :aria-pressed="c.id === store.cityId" :data-testid="`city-${c.id}`">
            <span class="city-name">{{ c.display_name }}</span>
            <span class="muted d-block">{{ c.country }}</span>
            <span class="badge-src badge-sample mt-2">sample data</span>
            <span class="d-block small mt-2">{{ c.currency_code }} · {{ c.counts.attractions }} sights · {{ c.counts.hotels }} fictional hotels</span>
          </button>
        </div>
      </div>
      <p v-if="city" class="small mb-0 mt-3"><strong>Using {{ city.display_name }}.</strong> {{ city.sample_fx_label }}</p>
    </section>

    <div class="card-soft d-flex flex-wrap gap-2 align-items-center" data-testid="demo-helpers">
      <strong class="me-2">Quick demo:</strong>
      <button class="btn btn-outline-primary btn-sm" @click="example('valid')" data-testid="load-example" :title="exLabel.title" :aria-describedby="'ex-note'">{{ exLabel.text }}</button>
      <button class="btn btn-outline-secondary btn-sm" @click="example('impossible')" data-testid="load-impossible">Try an impossible trip</button>
      <p id="ex-note" class="small muted mb-0 w-100" data-testid="example-note"><strong>About this example:</strong> it uses a high value of time ({{ exLabel.vot }} an hour) so that the hotel trade-off is visible. It is not typical: on random trips the cheapest hotel was usually also the best. See the measured result on the <router-link to="/evidence#hotel-value">Evidence page</router-link>.</p>
    </div>

    <NlParsePanel />

    <form class="card-soft" @submit.prevent="next" novalidate aria-label="Trip details">
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

        <div class="col-12 col-md-6">
          <label class="form-label" for="f-budget">Budget for sights and transport (optional)</label>
          <div class="input-group">
            <input id="f-budget" class="form-control" type="number" min="0" inputmode="numeric" v-model="store.form.budgetAmount" aria-describedby="budget-help" />
            <select class="form-select" style="max-width:6.5rem" v-model="store.form.budgetCurrency" aria-label="Budget currency"><option v-for="cur in currencyOptions" :key="cur">{{ cur }}</option></select>
          </div>
          <div id="budget-help" class="form-text">
            Covers admissions and estimated transport only, not rooms or food.
            <span v-if="city" data-testid="fx-note">{{ city.sample_fx_label }}<span v-if="budgetLocal"> → {{ formatLocalMoney(budgetLocal, city.currency_code) }}</span>.</span>
          </div>
          <div class="form-check form-switch mt-2">
            <input id="f-strict" class="form-check-input" type="checkbox" role="switch" v-model="store.form.strictBudget" :disabled="!store.form.budgetAmount && store.form.budgetAmount !== 0" />
            <label class="form-check-label" for="f-strict">Strict budget: never exceed it (otherwise it is a target)</label>
          </div>
        </div>
        <div class="col-12 col-md-6">
          <label class="form-label" for="f-pace">Pace</label>
          <select id="f-pace" class="form-select" v-model="store.form.pace" aria-describedby="pace-help">
            <option value="relaxed">Relaxed (up to 2 sights a day)</option>
            <option value="balanced">Balanced (up to 3 a day)</option>
            <option value="packed">Packed (up to 4 a day)</option>
          </select>
          <div id="pace-help" class="form-text">A hard cap on sights per day.</div>
        </div>

        <div class="col-12">
          <label class="form-label" for="f-vot">How much is an hour of your time worth? <strong data-testid="vot-value">{{ formatLocalMoney(vot, city?.currency_code ?? 'JPY') }} / hour</strong></label>
          <input id="f-vot" class="form-range" type="range" min="0" :max="city?.currency_code === 'KRW' ? 50000 : city?.currency_code === 'JPY' ? 5000 : 300" :step="city?.currency_code === 'KRW' ? 1000 : 1" v-model.number="store.form.valueOfTime" aria-describedby="vot-help" />
          <div id="vot-help" class="form-text">Used to compare hotels by true cost in {{ city?.currency_code ?? 'the city currency' }}.</div>
        </div>

        <div class="col-12 col-md-6">
          <div class="form-check">
            <input id="f-nights" class="form-check-input" type="checkbox" v-model="store.form.nightsOverride" />
            <label class="form-check-label" for="f-nights">Set the number of nights myself</label>
          </div>
          <input v-if="store.form.nightsOverride" id="f-nights-n" class="form-control mt-2" type="number" min="0" max="30" v-model.number="store.form.nights" aria-label="Number of nights" />
          <div class="form-text" data-testid="nights-used">Nights used for room cost: <strong>{{ nightsUsed(store.form) }}</strong> {{ store.form.nightsOverride ? '(your setting)' : '(default: days − 1)' }}</div>
        </div>
        <div class="col-12 col-md-6">
          <div class="form-check form-switch">
            <input id="f-unknown" class="form-check-input" type="checkbox" role="switch" v-model="store.form.allowUnknownHours" />
            <label class="form-check-label" for="f-unknown">Allow sights with unknown opening hours</label>
          </div>
          <div class="form-text">Off by default: if we do not know when a place is open, we never assume it is. If you turn this on, such stops are scheduled but flagged.</div>
        </div>
      </div>

      <div v-if="errors.length" class="notice notice-warn mt-3" role="alert" data-testid="form-errors">
        <span class="glyph" aria-hidden="true">!</span><ul class="mb-0 ps-3"><li v-for="e in errors" :key="e">{{ e }}</li></ul>
      </div>
      <div class="mt-3"><button type="submit" class="btn btn-primary" :disabled="errors.length > 0" data-testid="next-wishlist">Next: choose sights</button></div>
    </form>
  </div>
</template>
