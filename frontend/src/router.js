import { createRouter, createWebHistory } from 'vue-router'
import CreateTrip from './views/CreateTrip.vue'
import Wishlist from './views/Wishlist.vue'
import HotelCompare from './views/HotelCompare.vue'
import Itinerary from './views/Itinerary.vue'

export const routes = [
  { path: '/', name: 'create', component: CreateTrip, meta: { title: 'Plan your trip' } },
  { path: '/wishlist', name: 'wishlist', component: Wishlist, meta: { title: 'Choose sights' } },
  { path: '/hotels', name: 'hotels', component: HotelCompare, meta: { title: 'Compare hotels' } },
  { path: '/itinerary', name: 'itinerary', component: Itinerary, meta: { title: 'Itinerary' } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]
export const router = createRouter({ history: createWebHistory(), routes })
router.afterEach((to) => { document.title = `${to.meta.title ?? 'Trip'} · Tokyo Trip Planner` })
