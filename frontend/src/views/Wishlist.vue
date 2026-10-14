<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import AttractionCard from '../components/AttractionCard.vue'
import LoadingBlock from '../components/LoadingBlock.vue'
import ErrorPanel from '../components/ErrorPanel.vue'
import Skeleton from '../components/Skeleton.vue'
import { store, stateOf, setWish, loadPlaces } from '../store.js'
const router = useRouter()
const counts = computed(() => {
  const c = { must: 0, nice: 0, skip: 0 }
  for (const p of store.places ?? []) c[stateOf(p.id)]++
  return c
})
</script>
<template>
  <div class="stack">
    <div>
      <h1>Choose your sights</h1>
      <p class="muted mb-0">Mark must-sees, nice-to-haves and places you do not want. Optional sights may still be left out of the plan if they would cost more than they are worth; you will see which ones and why.</p>
    </div>
    <ErrorPanel v-if="store.placesError" :error="store.placesError" retryable @retry="loadPlaces" />
    <template v-else-if="!store.places"><LoadingBlock text="Loading places…" /><div class="row g-3"><div v-for="n in 6" :key="n" class="col-12 col-md-6 col-lg-4"><Skeleton :lines="5" /></div></div></template>
    <template v-else>
      <p class="mb-0" aria-live="polite" data-testid="wish-counts"><strong>{{ counts.must }}</strong> must visit · <strong>{{ counts.nice }}</strong> nice to have · <strong>{{ counts.skip }}</strong> not interested</p>
      <div class="row g-3">
        <div v-for="p in store.places" :key="p.id" class="col-12 col-md-6 col-lg-4">
          <AttractionCard :place="p" :state="stateOf(p.id)" :start-weekday="store.form.startWeekday" :days="store.form.days" :fx="store.fx" @update:state="setWish(p.id, $event)" />
        </div>
      </div>
      <div class="d-flex gap-2">
        <button class="btn btn-outline-secondary" @click="router.push('/')">Back</button>
        <button class="btn btn-primary" @click="router.push('/hotels')" data-testid="next-hotels">Next: compare hotels</button>
      </div>
    </template>
  </div>
</template>
