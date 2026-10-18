<script setup>
// Screen 1 of 2: choose everything, see it form (map + rough preview), then ONE action. Nothing here calls the solver or the AI except
// "Plan my trip" (an explicit click) and "Ask the AI" in the Describe box (an explicit click).
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import NlParsePanel from '../components/NlParsePanel.vue'
import AttractionCard from '../components/AttractionCard.vue'
import SightsMap from '../components/SightsMap.vue'
import PlanProgress from '../components/PlanProgress.vue'
import BusyNotice from '../components/BusyNotice.vue'
import ErrorPanel from '../components/ErrorPanel.vue'
import Hint from '../components/Hint.vue'
import Skeleton from '../components/Skeleton.vue'
import { exampleLabel } from '../lib/rules.js'
import { PITCH } from '../brand.js'
import { store, chooseProfile, noteProfileEdits, resetProfileOverrides, highlightThemes, toggleInterestTheme, currentPrefs, currentCityExamples, loadExample, requestCitySwitch, resetAll, planMyTrip, rateLimited, rateLimitSeconds, solverBusy, stateOf, setWish, loadPlaces } from '../store.js'
import { nightsUsed, budgetInJpy } from '../lib/prefs.js'
import { PROFILES, effective, profileName } from '../lib/profiles.js'
import { formatLocalMoney, WEEKDAY_NAMES, WEEKDAYS } from '../lib/format.js'
import { budgetSanityHint } from '../lib/tripSummary.js'
import { roughPreview } from '../lib/preview.js'
import { THEMES, countByTheme, isLimited, mixText, themeOf } from '../lib/themes.js'

const router = useRouter()
const errors = computed(() => currentPrefs().errors)
const city = computed(() => store.city)
const currencyOptions = computed(() => Array.from(new Set([city.value?.currency_code ?? 'JPY', city.value?.display_currency_code ?? 'SGD'])))
const budgetLocal = computed(() => budgetInJpy(store.form, city.value))
const budgetHint = computed(() => budgetSanityHint(store))
const vot = computed(() => Number(store.form.valueOfTime))
const effectiveRows = computed(() => effective(store.form, store.profile, store.city?.default_value_of_time_per_hour))
watch(() => [store.form.pace, store.form.maxActivities, store.form.maxDailyTravel, store.form.valueOfTime], noteProfileEdits)
const votDefault = computed(() => Number(city.value?.default_value_of_time_per_hour) || 1000)
const votPresets = computed(() => [
  { key: 'spend', label: 'Lower spending', value: Math.round(votDefault.value * 0.5) },
  { key: 'balanced', label: 'Balanced', value: votDefault.value },
  { key: 'time', label: 'Less travel time', value: votDefault.value * 4 },
])
const examplesForCity = computed(() => currentCityExamples.value)
const exLabel = computed(() => exampleLabel(examplesForCity.value.valid, city.value?.currency_code ?? 'JPY'))
const exTradeoff = computed(() => examplesForCity.value.valid.expect.rate_winner_differs_from_true_winner
  ? 'For this city, the pre-tested API result flips the hotel winner: the lowest nightly rate is not the best true cost.'
  : 'For this city, the pre-tested API result does not flip the hotel winner; it is still useful for trying the flow.')
const money = (v) => formatLocalMoney(v, city.value?.currency_code ?? 'JPY')

// ---- rough preview (no solver, no AI) ----
const preview = computed(() => roughPreview(store))
const counts = computed(() => { const c = { must: 0, nice: 0, skip: 0 }; for (const p of store.places ?? []) c[stateOf(p.id)]++; return c })
const center = computed(() => { const p = store.places?.[0]; return p ? [p.lat, p.lon] : [0, 0] })

// ---- the one action ----
const reason = computed(() => {
  if (errors.value.length) return errors.value[0]
  if (!store.places) return 'Sights are still loading.'
  if (!preview.value.total) return 'Pick at least one sight: every sight is set to "Not interested".'
  if (rateLimited.value) return `Too many requests. You can plan again in ${rateLimitSeconds.value} s.`
  if (solverBusy.value) return 'A plan is already being calculated.'
  return ''
})
async function plan() {
  if (reason.value) return
  const ok = await planMyTrip()
  if (ok) router.push('/trip')
}
function startOver() {
  if (!window.confirm('Clear this trip and start over?')) return
  resetAll()
  router.push('/')
}
const pickCity = requestCitySwitch
const hasPlan = computed(() => !!store.plan)
const busyError = computed(() => [store.planError, store.comparisonError].find((e) => e?.code === 'solver_busy') ?? null)
const realError = computed(() => [store.planError, store.comparisonError].find((e) => e && e.code !== 'solver_busy') ?? null)
const nudge = ref(false)

// ---- themes: tabs, counts, interests highlight (UI only; the planner uses Must / Include / Skip) ----
const themeCounts = computed(() => countByTheme(store.places))
const tabs = computed(() => [{ id: 'all', label: 'All', icon: '🗺️', count: (store.places ?? []).length, limited: false },
  ...THEMES.map((t) => ({ ...t, count: themeCounts.value[t.id], limited: isLimited(themeCounts.value[t.id]) }))])
const visiblePlaces = computed(() => {
  const list = (store.places ?? []).filter((p) => store.theme === 'all' || themeOf(p) === store.theme)
  const hi = highlightThemes.value
  return hi.size ? [...list].sort((a, b) => Number(hi.has(themeOf(b))) - Number(hi.has(themeOf(a)))) : list   // stable: highlighted sights first
})
const mustMix = computed(() => mixText((store.places ?? []).filter((p) => stateOf(p.id) === 'must')))
function onTabKey(e, i) {
  const n = tabs.value.length
  const to = e.key === 'ArrowRight' ? (i + 1) % n : e.key === 'ArrowLeft' ? (i + n - 1) % n : e.key === 'Home' ? 0 : e.key === 'End' ? n - 1 : null
  if (to === null) return
  e.preventDefault()
  store.theme = tabs.value[to].id
  document.getElementById(`tab-${tabs.value[to].id}`)?.focus()
}
const activeTab = computed(() => tabs.value.find((t) => t.id === store.theme) ?? tabs.value[0])
function example(kind) { loadExample(kind); nudge.value = true }
</script>
<template>
  <div class="stack">
    <div>
      <h1>Plan your trip</h1>
      <p class="fw-semibold mb-1" data-testid="pitch">{{ PITCH }}</p>
      <p class="muted mb-0">Choose the essentials and the sights you care about. One button then compares the hotels and plans your days. <Hint text="A hotel that looks cheap can cost more once travel time and fares are counted." /></p>
    </div>

    <NlParsePanel />

    <section class="card-soft" aria-labelledby="city-h">
      <h2 id="city-h" class="h6">City <span class="muted fw-normal small">(sample data: verify before real travel)</span></h2>
      <div class="city-chip-row" role="group" aria-label="Choose a city">
        <template v-if="!store.cities.length"><span v-for="n in 4" :key="`sk${n}`" class="city-pick skeleton" style="width:8rem" aria-hidden="true">&nbsp;</span></template>
        <button v-for="c in store.cities" :key="c.id" type="button" class="city-pick" :class="{ active: c.id === store.cityId }" @click="pickCity(c.id)" :aria-pressed="c.id === store.cityId" :data-testid="`city-${c.id}`">
          {{ c.display_name }} <span class="small fw-normal">· {{ c.currency_code }}</span>
        </button>
      </div>
      <p v-if="city" class="small mb-0 mt-2"><strong>Using {{ city.display_name }}, {{ city.country }}.</strong> {{ city.sample_fx_label }} Switching city asks first and clears what you have chosen.</p>
    </section>

    <div class="card-soft d-flex flex-wrap gap-2 align-items-center" data-testid="demo-helpers">
      <strong class="me-2">Try an example:</strong>
      <button class="btn btn-outline-primary btn-sm" @click="example('valid')" data-testid="load-example" :title="exLabel.title" :aria-describedby="'ex-note'">{{ exLabel.text }}</button>
      <button class="btn btn-outline-secondary btn-sm" @click="example('impossible')" data-testid="load-impossible">Try an impossible {{ city?.display_name ?? 'city' }} trip</button>
      <p id="ex-note" class="small muted mb-0 w-100" data-testid="example-note"><strong>About this example:</strong> this example uses a high value of time to illustrate the hotel trade-off. {{ exTradeoff }} It is not typical: on random trips the cheapest hotel was usually the best. See the <router-link to="/proof#hotel-value">Proof page</router-link>.
        <span v-if="nudge" role="status" data-testid="example-loaded"> The example is loaded below: check it, then press <strong>Plan my trip</strong>.</span></p>
    </div>


    <form class="card-soft" @submit.prevent="plan" novalidate aria-label="Trip essentials">
      <h2 class="h5">Essentials</h2>
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
        <div class="col-12 col-md-6">
          <label class="form-label" for="f-pace">Pace</label>
          <select id="f-pace" class="form-select" v-model="store.form.pace">
            <option value="relaxed">Relaxed (up to 2 sights a day)</option>
            <option value="balanced">Balanced (up to 3 a day)</option>
            <option value="packed">Packed (up to 4 a day)</option>
          </select>
        </div>
        <div class="col-12">
          <label class="form-label" for="f-budget">Budget for sights and transport (optional)</label>
          <div class="input-group" style="max-width:30rem">
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
      </div>

      <section class="mt-3" data-testid="profiles" aria-labelledby="prof-h">
        <h3 id="prof-h" class="h6 mb-1">Travel style <span class="muted fw-normal">(optional)</span></h3>
        <div class="d-flex flex-wrap gap-2" role="group" aria-label="Travel style">
          <button v-for="p in PROFILES" :key="p.id" type="button" class="btn btn-sm" :class="store.profile.id === p.id ? 'btn-primary' : 'btn-outline-primary'" :aria-pressed="store.profile.id === p.id" :data-testid="'profile-' + p.id" :title="p.blurb" @click="chooseProfile(p.id)">{{ p.label }}</button>
        </div>
        <p class="small muted mt-1 mb-1">A style only proposes values for pace, activities a day, estimated travel a day and the value of an hour. Change any of them yourself and your value is kept. It never changes your must-visits.</p>
        <div v-if="store.profile.id" class="small" data-testid="profile-effective">
          <strong data-testid="profile-name">{{ profileName(store.profile) }}</strong>
          <ul class="mb-1 ps-3"><li v-for="r in effectiveRows" :key="r.field" :data-testid="'eff-' + r.field">{{ r.label }}: <strong>{{ r.value }}</strong> <span class="pill">{{ r.source === 'you' ? 'set by you' : r.source === 'profile' ? 'from the style' : 'default' }}</span></li></ul>
          <button v-if="Object.keys(store.profile.user).length" type="button" class="btn btn-sm btn-link p-0" data-testid="profile-reset" @click="resetProfileOverrides">Go back to the style's own values</button>
        </div>
      </section>

      <details class="mt-3" data-testid="advanced">
        <summary class="fw-semibold">Advanced options</summary>
        <div class="row g-3 mt-1">
          <div class="col-6 col-md-3"><label class="form-label" for="f-start">Day starts</label><input id="f-start" class="form-control" type="time" v-model="store.form.dayStart" /></div>
          <div class="col-6 col-md-3"><label class="form-label" for="f-end">Day ends</label><input id="f-end" class="form-control" type="time" v-model="store.form.dayEnd" /></div>
          <div class="col-12 col-md-6">
            <label class="form-label" for="f-vot">Value of an hour of your time <Hint text="Travel time is priced at this rate when hotels are compared by true cost." /> <strong data-testid="vot-value">{{ money(vot) }} / hour</strong></label>
            <input id="f-vot" class="form-range" type="range" min="0" :max="city?.currency_code === 'KRW' ? 100000 : city?.currency_code === 'JPY' ? 5000 : 300" :step="city?.currency_code === 'KRW' ? 1000 : 1" v-model.number="store.form.valueOfTime" />
          </div>
          <div class="col-12 col-md-6" data-testid="vot-presets">
            <div class="form-label">Cost or convenience</div>
            <div class="btn-group btn-group-sm" role="group" aria-label="Cost or convenience">
              <button v-for="p in votPresets" :key="p.key" type="button" class="btn btn-outline-primary" :class="{ active: p.value === vot }" :data-testid="'vot-preset-' + p.key" @click="store.form.valueOfTime = p.value">{{ p.label }}</button>
            </div>
            <div class="form-text">These only set the value of an hour above (0.5×, 1× and 4× this city's default). Nothing else changes.</div>
          </div>
          <div class="col-6 col-md-3">
            <label class="form-label" for="f-maxact">Max activities per day <Hint text="Overrides the pace preset's cap. Leave blank to use the pace." /></label>
            <input id="f-maxact" class="form-control" type="number" min="1" max="8" placeholder="pace default" v-model="store.form.maxActivities" data-testid="max-activities" />
          </div>
          <div class="col-6 col-md-3">
            <label class="form-label" for="f-maxtravel">Max estimated travel per day (min) <Hint text="Estimated from straight-line distances in the sample data, not real routes. Leave blank for no limit." /></label>
            <input id="f-maxtravel" class="form-control" type="number" min="20" max="720" placeholder="no limit" v-model="store.form.maxDailyTravel" data-testid="max-daily-travel" />
          </div>
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
      <p class="small muted mb-0 mt-2" data-testid="state-retention-note">Your choices are kept while you move between steps. They are not saved if you refresh or close this page.</p>
    </form>

    <section aria-labelledby="sights-h" data-testid="sights-section">
      <div class="d-flex flex-wrap justify-content-between align-items-end gap-2 mb-2">
        <div>
          <h2 id="sights-h" class="h5 mb-0">Sights</h2>
          <p class="small muted mb-0">Mark must-sees; leave the rest as "Include if it fits" (left out if it adds too much travel) or choose "Not interested". <Hint text="Optional sights may still be left out of the plan if they would cost more than they are worth; you will see which ones and why." /></p>
        </div>
      </div>
      <p v-if="store.places" class="mb-2" aria-live="polite" data-testid="wish-counts"><strong>{{ counts.must }}</strong> must visit · <strong>{{ counts.nice }}</strong> include if it fits · <strong>{{ counts.skip }}</strong> not interested</p>
      <ErrorPanel v-if="store.placesError" :error="store.placesError" retryable @retry="loadPlaces" />
      <template v-else-if="!store.places"><div class="sight-grid"><Skeleton v-for="n in 6" :key="n" :lines="4" /></div></template>
      <div v-else class="plan-columns">
        <div>
          <div class="interest-row mb-2" role="group" aria-label="Interests (highlight only)" data-testid="interests">
            <span class="small fw-semibold me-1">Most interested in:</span>
            <button v-for="t in THEMES" :key="t.id" type="button" class="interest-chip" :aria-pressed="store.interestThemes.includes(t.id)" :data-testid="`interest-${t.id}`" @click="toggleInterestTheme(t.id)">
              <span aria-hidden="true">{{ t.icon }}</span> {{ t.label }}
            </button>
            <span class="small muted" data-testid="interest-hint">This only highlights. The planner uses your Must / Include / Skip choices.</span>
          </div>
          <div class="theme-tabs" role="tablist" aria-label="Sight themes" data-testid="theme-tabs">
            <button v-for="(t, i) in tabs" :key="t.id" :id="`tab-${t.id}`" type="button" role="tab" class="theme-tab" :aria-selected="store.theme === t.id" :aria-controls="'sight-panel'"
              :tabindex="store.theme === t.id ? 0 : -1" :data-testid="`tab-${t.id}`" @click="store.theme = t.id" @keydown="onTabKey($event, i)">
              <span aria-hidden="true">{{ t.icon }}</span> <span>{{ t.label }}</span> <span class="theme-count" :aria-label="`${t.count} sights`">{{ t.count }}</span>
              <span v-if="t.limited" class="theme-limited" data-testid="limited-note">Limited in the sample data</span>
            </button>
          </div>
          <p v-if="mustMix" class="small mb-2" data-testid="theme-selected" aria-live="polite">Your must-visits: {{ mustMix }}.</p>
          <div id="sight-panel" role="tabpanel" :aria-labelledby="`tab-${store.theme}`" tabindex="-1" data-testid="sight-panel">
            <div class="sight-grid" data-testid="sight-grid">
              <AttractionCard v-for="p in visiblePlaces" :key="p.id" :place="p" :state="stateOf(p.id)" :start-weekday="store.form.startWeekday" :days="store.form.days" :fx="store.fx" compact
                :highlight="highlightThemes.has(themeOf(p))" @update:state="setWish(p.id, $event)" />
            </div>
          </div>
        </div>
        <div class="plan-map-col stack">
          <SightsMap :places="store.places" :wishlist="store.wishlist" :center="center" />
          <section class="card-soft" aria-labelledby="prev-h" data-testid="rough-preview">
            <h3 id="prev-h" class="h6">Rough preview <span class="badge-src badge-estimated">not a plan</span></h3>
            <p class="small mb-1" data-testid="preview-count"><strong>{{ preview.mustCount }}</strong> must visit · <strong>{{ preview.maybeCount }}</strong> include if it fits · at most <strong>{{ preview.maxFit }}</strong> sights fit in {{ store.form.days }} day(s) at this pace.</p>
            <p v-if="preview.mustOverCap" class="small mb-1" style="color: var(--amber)" data-testid="preview-overcap"><span aria-hidden="true">!</span> You marked more must-visits than fit at this pace; the planner will explain what cannot fit.</p>
            <p v-if="preview.mix" class="small mb-1" data-testid="preview-mix">Theme mix in the running: {{ preview.mix }}.</p>
            <p class="small mb-1" data-testid="preview-admissions">Known admissions for your must-visits: <strong>{{ money(preview.mustAdmissions) }}</strong>; if every sight in the running fitted: up to <strong>{{ money(preview.allAdmissions) }}</strong>.</p>
            <p v-if="preview.allUnknown.length" class="small mb-1" data-testid="preview-unknown">Unknown price (not counted): {{ preview.allUnknown.join(', ') }}.</p>
            <p class="small mb-0" data-testid="preview-areas">Areas in the running: {{ preview.areas.join(', ') || 'none' }}.</p>
            <p class="small muted mb-0 mt-1">Computed from the sample data in your browser. Travel time, order and what really fits come from the planner.</p>
          </section>
        </div>
      </div>
    </section>

    <div class="plan-bar" data-testid="plan-bar">
      <div class="page-inner stack">
        <BusyNotice :error="busyError" @retry="plan" />
        <ErrorPanel v-if="realError" :error="realError" />
        <PlanProgress />
        <div class="d-flex flex-wrap align-items-center gap-3">
          <button type="button" class="btn btn-primary btn-lg" :disabled="!!reason" :aria-describedby="reason ? 'plan-reason' : 'plan-summary'" @click="plan" data-testid="plan-trip">
            {{ store.stage ? 'Planning…' : hasPlan ? 'Plan my trip again' : 'Plan my trip' }}
          </button>
          <span id="plan-summary" class="small" aria-live="polite" data-testid="plan-summary">{{ preview.total }} sight(s) in the running · {{ preview.mustCount }} must visit</span>
          <span v-if="reason" id="plan-reason" class="small" data-testid="plan-reason"><span aria-hidden="true">!</span> {{ reason }}</span>
          <router-link v-if="hasPlan" to="/trip" class="small" data-testid="back-to-trip">Back to my trip</router-link>
          <button type="button" class="btn btn-link btn-sm ms-auto" @click="startOver" data-testid="start-over">Start over</button>
        </div>
      </div>
    </div>
  </div>
</template>
