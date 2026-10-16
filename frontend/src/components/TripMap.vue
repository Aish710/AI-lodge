<script setup>
// Leaflet map of the plan. Per-day colour AND shape AND number on every pin; hotel pin; polylines in stop order (hotel legs dashed).
// Popup text is built with textContent, never HTML strings. Tiles degrade to a plain background (lib/tiles.js).
// Added in the final phase: a day filter, filter chips (icon + text + count), pins that overlap are spread out (spiderfy-lite, recomputed on zoom),
// and hovering or focusing a pin highlights its card (and the other way round).
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { dayColor, dayShape } from '../lib/mapstyle.js'
import { attachBaseLayer } from '../lib/tiles.js'
import { THEMES, themeLabel, themeOf } from '../lib/themes.js'

const props = defineProps({ days: { type: Array, default: () => [] }, hotel: { type: Object, default: null }, placesById: { type: Object, required: true },
  selectedDay: { type: [String, Number], default: 'all' }, activeStop: { type: String, default: null } })
const emit = defineEmits(['select-stop', 'hover-stop'])
const el = ref(null)
const tilesOff = ref(false)
let map = null
let layer = null
let ro = null
let base = null
let fitted = ''
const markers = new Map()   // attraction id -> Leaflet marker (the active-pin highlight and the card link use it)

const CHIPS = [
  { id: 'sightseeing', label: 'Attractions', icon: '🏛️', kind: 'theme' },
  { id: 'food', label: 'Food', icon: '🍜', kind: 'theme' },
  { id: 'shopping', label: 'Shopping', icon: '🛍️', kind: 'theme' },
  { id: 'hotels', label: 'Hotels', icon: '🏨', kind: 'hotels' },
  { id: 'saved', label: 'Saved', icon: '⭐', kind: 'only', hint: 'Show only your Must visit picks' },
  { id: 'booking', label: 'Needs booking', icon: '🎟️', kind: 'only', hint: 'Show only sights that need advance booking' },
]
const on = reactive({ sightseeing: true, food: true, shopping: true, hotels: true, saved: false, booking: false })

const viewDays = computed(() => props.days.filter((d) => props.selectedDay === 'all' || d.day === props.selectedDay))
const themeOfStop = (s) => { const p = props.placesById[s.attraction_id]; return p ? themeOf(p) : 'sightseeing' }
const stopsInView = computed(() => viewDays.value.flatMap((d) => d.stops.map((s) => ({ d, s }))))
const counts = computed(() => ({
  sightseeing: stopsInView.value.filter(({ s }) => themeOfStop(s) === 'sightseeing').length,
  food: stopsInView.value.filter(({ s }) => themeOfStop(s) === 'food').length,
  shopping: stopsInView.value.filter(({ s }) => themeOfStop(s) === 'shopping').length,
  hotels: props.hotel ? 1 : 0,
  saved: stopsInView.value.filter(({ s }) => s.is_must_visit).length,
  booking: stopsInView.value.filter(({ s }) => (s.uncertainty_flags ?? []).includes('advance_booking_required')).length,
}))
const visibleStop = ({ s }) => on[themeOfStop(s)] && (!on.saved || s.is_must_visit) && (!on.booking || (s.uncertainty_flags ?? []).includes('advance_booking_required'))

function pinIcon(num, color, shape, size = 56) {
  const html = `<div class="pin-visual"><div class="pin pin-${shape}" style="background:${color};width:${size}px;height:${size}px"><span>${Number(num)}</span></div></div>`
  const hit = 24
  return L.divIcon({ className: 'pin-hit-target', html, iconSize: [hit, hit], iconAnchor: [hit / 2, hit / 2], popupAnchor: [0, -hit / 2] })
}
function popup(lines) {
  const box = document.createElement('div')
  lines.forEach((t, i) => { const d = document.createElement(i === 0 ? 'strong' : 'div'); d.textContent = t; box.appendChild(d) })
  return box
}

/** Overlapping pins: anything closer than MIN_PX on screen is moved onto a small ring around its true position (only the pin moves, never the data). */
const MIN_PX = 30
function spread(points) {
  const placed = points.map((p) => ({ ...p, px: map.latLngToLayerPoint(p.latlng) }))
  const used = new Set()
  const out = new Map()
  placed.forEach((a, i) => {
    if (used.has(i)) return
    const group = placed.map((b, j) => ({ b, j })).filter(({ b, j }) => !used.has(j) && a.px.distanceTo(b.px) < MIN_PX)
    group.forEach(({ j }) => used.add(j))
    if (group.length === 1) { out.set(a.key, a.latlng); return }
    const r = MIN_PX * 0.75 + group.length * 2
    group.forEach(({ b }, k) => {
      const ang = (2 * Math.PI * k) / group.length - Math.PI / 2
      out.set(b.key, map.layerPointToLatLng(a.px.add(L.point(r * Math.cos(ang), r * Math.sin(ang)))))
    })
  })
  return out
}

function draw(refit = true) {
  if (!map) return
  layer.clearLayers()
  markers.clear()
  const hotel = props.hotel
  const hp = hotel ? [hotel.lat, hotel.lon] : null
  const fitPts = []
  const items = []
  if (hp && on.hotels) { fitPts.push(hp); items.push({ key: 'hotel', latlng: L.latLng(hp) }) }
  for (const d of viewDays.value) {
    const coords = d.stops.map((s) => props.placesById[s.attraction_id]).filter(Boolean).map((p) => [p.lat, p.lon])
    if (coords.length) {
      const color = dayColor(d.day)
      if (hp) {
        L.polyline([hp, coords[0]], { color, weight: 3, opacity: 0.8, dashArray: '4 6' }).addTo(layer)
        L.polyline([coords[coords.length - 1], hp], { color, weight: 3, opacity: 0.8, dashArray: '4 6' }).addTo(layer)
      }
      if (coords.length > 1) L.polyline(coords, { color, weight: 4, opacity: 0.9 }).addTo(layer)
    }
    d.stops.forEach((s, i) => {
      const p = props.placesById[s.attraction_id]
      if (!p || !visibleStop({ s })) return
      fitPts.push([p.lat, p.lon])
      items.push({ key: `${d.day}:${s.attraction_id}`, latlng: L.latLng(p.lat, p.lon), d, s, i, p })
    })
  }
  const key = `${props.selectedDay}|${fitPts.map((q) => q.join(',')).join('|')}`
  if (refit && key !== fitted) {
    fitted = key
    if (fitPts.length) map.fitBounds(L.latLngBounds(fitPts), { padding: [40, 40], maxZoom: 14 })
    else map.setView(hp ?? [0, 0], 11)
  }
  const placed = spread(items)
  for (const it of items) {
    const at = placed.get(it.key)
    if (it.key === 'hotel') {
      const m = L.marker(at, { icon: L.divIcon({ className: 'pin-hit-target', html: '<div class="pin-visual"><div class="pin pin-hotel" style="width:56px;height:56px"><span>H</span></div></div>', iconSize: [24, 24], iconAnchor: [12, 12], popupAnchor: [0, -12] }),
        title: `Hotel: ${hotel.name} (demo hotel)`, alt: `Hotel ${hotel.name}`, keyboard: true }).bindPopup(popup([hotel.name, 'Demo hotel'])).addTo(layer)
      m.getElement()?.setAttribute('aria-label', `Hotel: ${hotel.name} (demo hotel)`)
      continue
    }
    const { d, s, i, p } = it
    const label = `Day ${d.day}, stop ${i + 1}: ${p.name} (${themeLabel(p)}), ${s.start} to ${s.end}`
    const marker = L.marker(at, { icon: pinIcon(i + 1, dayColor(d.day), dayShape(d.day)), title: label, alt: label, keyboard: true })
      .bindPopup(popup([`${i + 1}. ${p.name}`, `${themeLabel(p)} · Day ${d.day} (${dayShape(d.day)}), ${s.start}-${s.end}`])).addTo(layer)
    const elx = marker.getElement()
    elx?.setAttribute('aria-label', label)
    elx?.addEventListener('focus', () => emit('hover-stop', s.attraction_id))
    elx?.addEventListener('blur', () => emit('hover-stop', null))
    marker.on('mouseover', () => emit('hover-stop', s.attraction_id))
    marker.on('mouseout', () => emit('hover-stop', null))
    marker.on('click', () => emit('select-stop', { attractionId: s.attraction_id, day: d.day, index: i }))
    marker.on('keydown', (e) => {
      if (e.originalEvent?.key === 'Enter' || e.originalEvent?.key === ' ') {
        e.originalEvent.preventDefault()
        marker.openPopup()
        emit('select-stop', { attractionId: s.attraction_id, day: d.day, index: i })
      }
    })
    markers.set(s.attraction_id, marker)
  }
  markActive()
}
function markActive() {
  for (const [id, m] of markers) m.getElement()?.classList.toggle('pin-active', id === props.activeStop)
}

onMounted(() => {
  map = L.map(el.value, { scrollWheelZoom: false, zoomControl: true })
  base = attachBaseLayer(map, { onUnavailable: () => { tilesOff.value = true } })
  layer = L.layerGroup().addTo(map)
  map.setView([0, 0], 2)
  draw()
  map.on('zoomend', () => draw(false))            // the screen distance between pins changes with zoom
  // Leaflet must be told when its container changes size (layout settles after mount, window resizes), or tiles only fill part of the map.
  ro = new ResizeObserver(() => { map?.invalidateSize(); draw(false) })
  ro.observe(el.value)
})
watch(() => [props.days, props.hotel, props.placesById, props.selectedDay], () => draw(), { deep: true })
watch(() => [on.sightseeing, on.food, on.shopping, on.hotels, on.saved, on.booking], () => draw())
watch(() => props.activeStop, markActive)
onBeforeUnmount(() => { base?.dispose(); ro?.disconnect(); map?.remove(); map = null })
</script>
<template>
  <div>
    <div class="map-chips mb-2" role="group" aria-label="Map filters" data-testid="map-chips">
      <button v-for="c in CHIPS" :key="c.id" type="button" class="map-chip" :aria-pressed="on[c.id]" :title="c.hint" :data-testid="`chip-${c.id}`" @click="on[c.id] = !on[c.id]">
        <span aria-hidden="true">{{ c.icon }}</span> {{ c.label }} <span class="theme-count">{{ counts[c.id] }}</span>
      </button>
    </div>
    <div ref="el" class="map-wrap" :class="{ 'map-plain': tilesOff }" role="region" aria-label="Map of the itinerary: hotel and numbered stops per day. The day-by-day list next to it has the same information." data-testid="trip-map"></div>
    <p v-if="tilesOff" class="small muted mt-1 mb-0" role="status" data-testid="tiles-unavailable">Map tiles unavailable. The pins are still in the right places, and the list next to the map has the same information.</p>
    <div class="small muted mt-1" data-testid="map-legend">
      <span v-for="d in days" :key="d.day" class="me-3 d-inline-flex align-items-center gap-1">
        <span class="marker" :class="`shape-${dayShape(d.day)}`" :style="{ '--day': dayColor(d.day), width: '16px', height: '16px', fontSize: '.6rem' }" aria-hidden="true"></span>
        Day {{ d.day }} ({{ dayShape(d.day) }})
      </span>
      <span class="d-inline-flex align-items-center gap-1"><span class="pin pin-hotel" style="width:16px;height:16px;font-size:.6rem" aria-hidden="true">H</span> Hotel · dashed line = to/from the hotel</span>
      <span class="d-block">"Saved" = your Must visit picks. No airports or stations: the sample data has none.</span>
    </div>
  </div>
</template>
