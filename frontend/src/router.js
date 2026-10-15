import { createRouter, createWebHistory } from 'vue-router'
import Plan from './views/Plan.vue'
import { PROJECT_NAME } from './brand.js'

export const routes = [
  { path: '/', name: 'plan', component: Plan, meta: { title: 'Plan your trip' } },
  { path: '/trip', name: 'trip', component: () => import('./views/Trip.vue'), meta: { title: 'Your trip' } },
  // the five-step addresses keep working (bookmarks, old links)
  { path: '/wishlist', redirect: '/' },
  { path: '/hotels', redirect: '/trip' },
  { path: '/itinerary', redirect: '/trip' },
  { path: '/proof', name: 'proof', component: () => import('./views/Proof.vue'), meta: { title: 'Proof' } },
  { path: '/how-it-works', name: 'how-it-works', component: () => import('./views/HowItWorks.vue'), meta: { title: 'How it works' } },
  // the old names keep working (external links, bookmarks), including the #section part
  { path: '/evidence', redirect: (to) => ({ path: '/proof', hash: to.hash }) },
  { path: '/about', redirect: (to) => ({ path: '/how-it-works', hash: to.hash }) },
  { path: '/:pathMatch(.*)*', name: 'notfound', component: () => import('./views/NotFound.vue'), meta: { title: 'Page not found' } },
]
export const router = createRouter({
  history: createWebHistory(), routes,
  scrollBehavior(to) { return to.hash ? { el: to.hash, top: 70 } : { top: 0 } },
})
router.afterEach((to) => { document.title = `${to.meta.title ?? 'Trip'} · ${PROJECT_NAME}` })
// Keyboard and screen-reader users: after navigating, move focus to the main region so the new page is announced from its start.
router.afterEach(() => { setTimeout(() => document.getElementById('main')?.focus({ preventScroll: true }), 0) })
