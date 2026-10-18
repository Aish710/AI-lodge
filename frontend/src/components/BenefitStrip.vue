<script setup>
// What the sample-data evidence says about the planner's itinerary, for THIS city. Every number comes from benefits.json, generated from docs/itinerary-study.json.
// It is a statement about seeded synthetic trips, not a prediction for this trip, and it names the cases where the planner made no difference.
import { computed } from 'vue'
import { store } from '../store.js'
import data from '../lib/benefits.json'

const b = computed(() => data.cities?.[store.cityId] ?? null)
const cityName = computed(() => store.city?.display_name ?? store.cityId)
</script>
<template>
  <section v-if="b" class="small border rounded p-2" data-testid="benefit-strip" aria-labelledby="ben-h">
    <h2 id="ben-h" class="h6 mb-1">What the sample evidence says about plans like this</h2>
    <ul class="mb-1 ps-3">
      <li data-testid="ben-feasible">In {{ b.trips }} generated {{ cityName }} trips, a plan that follows your listed order and the opening hours kept every must-visit in {{ b.input_order_feasible }}; the planner did in {{ b.optimiser_feasible }}. In {{ b.input_order_missed_a_must_where_optimiser_found_plan }} trips the listed-order plan missed a must-visit where the planner found a plan that included it.</li>
      <li data-testid="ben-routing">For exactly the same sights ({{ b.matched_solved }} trips), the planner's order had less estimated travel in {{ b.minutes_better }}, the same in {{ b.minutes_equal }} and more in {{ b.minutes_worse }}<span v-if="b.minutes_median !== null"> (median difference {{ b.minutes_median }} min, largest {{ b.minutes_max }} min)</span>.</li>
    </ul>
    <p class="muted mb-0">Seeded synthetic trips on sample data with estimated travel times, not a prediction for your trip. <router-link to="/proof#itinerary">See the full study</router-link>.</p>
  </section>
</template>
