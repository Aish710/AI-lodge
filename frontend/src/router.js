import { createRouter, createWebHistory } from 'vue-router'
import CreateTrip from './views/CreateTrip.vue'
import { PROJECT_NAME } from './brand.js'

export const routes = [
  { path: '/', name: 'create', component: CreateTrip, meta: { title: 'Plan your trip' } },
  { path: '/wishlist', name: 'wishlist', component: () => import('./views/Wishlist.vue'), meta: { title: 'Choose sights' } },
  { path: '/hotels', name: 'hotels', component: () => import('./views/HotelCompare.vue'), meta: { title: 'Compare hotels' } },
  { path: '/itinerary', name: 'itinerary', component: () => import('./views/Itinerary.vue'), meta: { title: 'Itinerary' } },
  { path: '/evidence', name: 'evidence', component: () => import('./views/Evidence.vue'), meta: { title: 'Evidence' } },
  { path: '/about', name: 'about', component: () => import('./views/About.vue'), meta: { title: 'About' } },
  { path: '/:pathMatch(.*)*', name: 'notfound', component: () => import('./views/NotFound.vue'), meta: { title: 'Page not found' } },
]
export const router = createRouter({
  history: createWebHistory(), routes,
  scrollBehavior(to) { return to.hash ? { el: to.hash, top: 70 } : { top: 0 } },
})
router.afterEach((to) => { document.title = `${to.meta.title ?? 'Trip'} · ${PROJECT_NAME}` })
// Keyboard and screen-reader users: after navigating, move focus to the main region so the new page is announced from its start.
router.afterEach(() => { setTimeout(() => document.getElementById('main')?.focus({ preventScroll: true }), 0) })
