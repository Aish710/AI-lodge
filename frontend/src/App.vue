<script setup>
import { computed, onBeforeUnmount, onMounted } from 'vue'
import HonestyBanner from './components/HonestyBanner.vue'
import ModeIndicator from './components/ModeIndicator.vue'
import CityChip from './components/CityChip.vue'
import ServerStatus from './components/ServerStatus.vue'
import RateLimitNotice from './components/RateLimitNotice.vue'
import { useRouter } from 'vue-router'
import ConfirmDialog from './components/ConfirmDialog.vue'
import { boot, store, resetAll, selectCity } from './store.js'
import { clearedOnCitySwitch } from './lib/names.js'
import { hasUnsavedWork } from './lib/tripSummary.js'
import { PROJECT_NAME, REPO_URL } from './brand.js'
const router = useRouter()
function reset() { resetAll(); router.push('/') }
const pendingName = computed(() => store.cities.find((c) => c.id === store.pendingCity)?.display_name ?? '')
async function confirmSwitch() {
  const id = store.pendingCity
  store.pendingCity = null
  if (id) { await selectCity(id); router.push('/') }
}
function beforeUnload(e) {
  if (!hasUnsavedWork(store)) return
  e.preventDefault()
  e.returnValue = ''
}
onMounted(() => {
  boot()
  window.addEventListener('beforeunload', beforeUnload)
})
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnload))
</script>
<template>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="page d-flex flex-wrap align-items-center justify-content-between gap-2 py-2">
      <router-link to="/" class="wordmark"><span class="dot" aria-hidden="true"></span>{{ PROJECT_NAME }}</router-link>
      <nav aria-label="Steps">
        <ul class="nav-steps">
          <li><router-link to="/" exact-active-class="router-link-active">1 Trip</router-link></li>
          <li><router-link to="/wishlist">2 Sights</router-link></li>
          <li><router-link to="/hotels">3 Hotels</router-link></li>
          <li><router-link to="/itinerary">4 Itinerary</router-link></li>
          <li><router-link to="/evidence">Evidence</router-link></li>
          <li><router-link to="/about">About</router-link></li>
        </ul>
      </nav>
    </div>
  </header>
  <HonestyBanner />
  <main id="main" class="page pt-3" tabindex="-1">
    <div class="stack mb-3">
      <div class="d-flex flex-wrap gap-2 align-items-center mode-slot"><CityChip /><ModeIndicator /></div>
      <ServerStatus />
      <RateLimitNotice />
    </div>
    <router-view v-if="store.server === 'ready'" />
    <p v-else-if="store.server !== 'down'" class="muted" aria-live="polite">The planner will appear as soon as the server answers.</p>
  </main>
  <ConfirmDialog v-if="store.pendingCity" :open="true" :title="`Switch to ${pendingName}?`" confirm-label="Switch and clear" cancel-label="Keep current city" @confirm="confirmSwitch" @cancel="store.pendingCity = null">
    <p class="mb-2">One trip covers one city, so switching to {{ pendingName }} will clear:</p>
    <ul class="mb-0" data-testid="switch-clears"><li v-for="item in clearedOnCitySwitch(store)" :key="item">{{ item }}</li></ul>
  </ConfirmDialog>
  <footer class="page site-footer" data-testid="footer">
    <p class="mb-1"><strong>Privacy:</strong> what you type stays in this page's memory. It is sent to the planner's server only to compute results, and the server does not store it. No cookies, no analytics, no third-party scripts. The map loads tiles from OpenStreetMap, which sees your IP address and the map area you view.</p>
    <p class="mb-1">All places, prices, hours and travel times are samples or estimates. Hotels are fictional. Details: <router-link to="/about#privacy">About and privacy</router-link> · <router-link to="/evidence">Evidence</router-link></p>
    <p class="mb-0">{{ PROJECT_NAME }} · <a :href="REPO_URL" target="_blank" rel="noopener noreferrer">Source on GitHub</a> ·
      <button type="button" class="btn btn-link btn-sm p-0 align-baseline" @click="reset" data-testid="reset">Reset (clear everything held in this page)</button></p>
  </footer>
</template>
