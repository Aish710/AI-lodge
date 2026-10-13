<script setup>
// Leaflet map over OpenStreetMap tiles (attribution visible). Per-day colour AND shape AND number on every pin; hotel pin; polylines in
// stop order (hotel legs dashed). Popup text is built with textContent, never HTML strings, so place names cannot inject markup.
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { dayColor, dayShape } from '../lib/mapstyle.js'

const props = defineProps({ days: { type: Array, default: () => [] }, hotel: { type: Object, default: null }, placesById: { type: Object, required: true } })
const el = ref(null)
let map = null
let layer = null
let ro = null

function pinIcon(num, color, shape, size = 30) {
  const html = `<div class="pin pin-${shape}" style="background:${color};width:${size}px;height:${size}px"><span>${Number(num)}</span></div>`
  return L.divIcon({ className: '', html, iconSize: [size, size], iconAnchor: [size / 2, size / 2], popupAnchor: [0, -size / 2] })
}
function popup(lines) {
  const box = document.createElement('div')
  lines.forEach((t, i) => { const d = document.createElement(i === 0 ? 'strong' : 'div'); d.textContent = t; box.appendChild(d) })
  return box
}

function draw() {
  if (!map) return
  layer.clearLayers()
  const pts = []
  const hotel = props.hotel
  const hp = hotel ? [hotel.lat, hotel.lon] : null
  if (hp) {
    pts.push(hp)
    L.marker(hp, { icon: L.divIcon({ className: '', html: '<div class="pin pin-hotel" style="width:30px;height:30px"><span>H</span></div>', iconSize: [30, 30], iconAnchor: [15, 15], popupAnchor: [0, -15] }),
      title: `Hotel: ${hotel.name} (fictional)`, alt: `Hotel ${hotel.name}`, keyboard: true })
      .bindPopup(popup([hotel.name, 'Hotel (fictional)'])).addTo(layer)
  }
  for (const d of props.days) {
    const color = dayColor(d.day)
    const shape = dayShape(d.day)
    const coords = d.stops.map((s) => props.placesById[s.attraction_id]).filter(Boolean).map((p) => [p.lat, p.lon])
    if (!coords.length) continue
    if (hp) {
      L.polyline([hp, coords[0]], { color, weight: 3, opacity: 0.8, dashArray: '4 6' }).addTo(layer)
      L.polyline([coords[coords.length - 1], hp], { color, weight: 3, opacity: 0.8, dashArray: '4 6' }).addTo(layer)
    }
    if (coords.length > 1) L.polyline(coords, { color, weight: 4, opacity: 0.9 }).addTo(layer)
    d.stops.forEach((s, i) => {
      const p = props.placesById[s.attraction_id]
      if (!p) return
      pts.push([p.lat, p.lon])
      L.marker([p.lat, p.lon], { icon: pinIcon(i + 1, color, shape), title: `Day ${d.day}, stop ${i + 1}: ${p.name}`, alt: `Day ${d.day} stop ${i + 1} ${p.name}`, keyboard: true })
        .bindPopup(popup([`${i + 1}. ${p.name}`, `Day ${d.day} (${shape}), ${s.start}-${s.end}`])).addTo(layer)
    })
  }
  if (pts.length) map.fitBounds(L.latLngBounds(pts), { padding: [30, 30], maxZoom: 14 })
  else map.setView([35.68, 139.76], 11)
}

onMounted(() => {
  map = L.map(el.value, { scrollWheelZoom: false, zoomControl: true })
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
  }).addTo(map)
  layer = L.layerGroup().addTo(map)
  draw()
  // Leaflet must be told when its container changes size (layout settles after mount, window resizes), or tiles only fill part of the map.
  ro = new ResizeObserver(() => { map?.invalidateSize() })
  ro.observe(el.value)
})
watch(() => [props.days, props.hotel, props.placesById], draw, { deep: true })
onBeforeUnmount(() => { ro?.disconnect(); map?.remove(); map = null })
</script>
<template>
  <div>
    <div ref="el" class="map-wrap" role="region" aria-label="Map of the itinerary: hotel and numbered stops per day. The day-by-day list next to it has the same information." data-testid="trip-map"></div>
    <div class="small muted mt-1" data-testid="map-legend">
      <span v-for="d in days" :key="d.day" class="me-3 d-inline-flex align-items-center gap-1">
        <span class="marker" :class="`shape-${dayShape(d.day)}`" :style="{ '--day': dayColor(d.day), width: '16px', height: '16px', fontSize: '.6rem' }" aria-hidden="true"></span>
        Day {{ d.day }} ({{ dayShape(d.day) }})
      </span>
      <span class="d-inline-flex align-items-center gap-1"><span class="pin pin-hotel" style="width:16px;height:16px;font-size:.6rem" aria-hidden="true">H</span> Hotel · dashed line = to/from the hotel</span>
    </div>
  </div>
</template>
