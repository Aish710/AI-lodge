<script setup>
// Plan screen map: pins for the sights still in the running. Must = dark square "M", Include if it fits = white circle "+". Moving the choices only redraws
// pins (no request, no solver). Popup text is built with textContent. Tiles degrade to a plain background (see lib/tiles.js).
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { attachBaseLayer } from '../lib/tiles.js'
import { stateOf, setWish } from '../store.js'
import { themeIcon, themeLabel } from '../lib/themes.js'
import { iconSvg } from '../lib/icons.js'
import Icon from './Icon.vue'

const props = defineProps({ places: { type: Array, default: () => [] }, wishlist: { type: Object, default: () => ({}) }, center: { type: Array, default: () => [0, 0] } })
const el = ref(null)
const tilesOff = ref(false)
let map = null
let layer = null
let ro = null
let base = null
let fitted = ''

function icon(kind, glyph) {
  const html = `<div class="pin-visual"><div class="pin pin-${kind}" style="width:30px;height:30px"><span>${glyph}</span></div></div>`
  return L.divIcon({ className: 'pin-hit-target', html, iconSize: [24, 24], iconAnchor: [12, 12], popupAnchor: [0, -12] })
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
  for (const p of props.places) {
    const state = stateOf(p.id)
    if (state === 'skip') continue
    const kind = state === 'must' ? 'must' : 'nice'
    const label = `${p.name}, ${p.area}, ${themeLabel(p)}: ${kind === 'must' ? 'must visit' : 'include if it fits'}`
    pts.push([p.lat, p.lon])
    const content = popup([p.name, `${themeLabel(p)} · ${p.area} · ${kind === 'must' ? 'Must visit' : 'Include if it fits'}`])
    const choice = document.createElement('button')
    choice.type = 'button'; choice.className = 'btn btn-sm btn-outline-primary mt-2'
    choice.textContent = kind === 'must' ? 'Include if it fits' : 'Mark as must visit'
    choice.addEventListener('click', () => setWish(p.id, kind === 'must' ? 'nice' : 'must'))
    content.appendChild(choice)
    const m = L.marker([p.lat, p.lon], { icon: icon(kind, iconSvg(themeIcon(p), 16)), title: label, alt: label, keyboard: true })
      .bindPopup(content).addTo(layer)
    m.getElement()?.setAttribute('aria-label', label)   // the marker is already on the map, so its element exists now ('add' has already fired)
    m.on('add', () => m.getElement()?.setAttribute('aria-label', label))
    m.on('keydown', (e) => { if (e.originalEvent?.key === 'Enter' || e.originalEvent?.key === ' ') { e.originalEvent.preventDefault(); m.openPopup() } })
  }
  // Re-fit only when the set of pins changes, so a pin you are about to click does not slide away.
  const key = pts.map((q) => q.join(',')).join('|')
  if (key !== fitted) {
    fitted = key
    if (pts.length) map.fitBounds(L.latLngBounds(pts), { padding: [30, 30], maxZoom: 14 })
    else map.setView(props.center, 11)
  }
}
onMounted(() => {
  map = L.map(el.value, { scrollWheelZoom: false, zoomControl: true })
  base = attachBaseLayer(map, { onUnavailable: () => { tilesOff.value = true } })
  layer = L.layerGroup().addTo(map)
  draw()
  ro = new ResizeObserver(() => {
    if (!el.value?.clientWidth || !el.value?.clientHeight) return
    map?.invalidateSize(); fitted = ''; draw()
  })
  ro.observe(el.value)
})
watch(() => [props.places, props.center, JSON.stringify(props.wishlist)], draw, { deep: true })
onBeforeUnmount(() => { base?.dispose(); ro?.disconnect(); map?.remove(); map = null })
</script>
<template>
  <div>
    <div ref="el" class="map-wrap" :class="{ 'map-plain': tilesOff }" role="region" aria-label="Map of the sights you are considering. The list beside it has the same information and the same choices." data-testid="sights-map"></div>
    <p v-if="tilesOff" class="small muted mt-1 mb-0" role="status" data-testid="tiles-unavailable">Map tiles unavailable. The pins are still in the right places, and the list next to the map has the same information.</p>
    <p class="small muted mt-1 mb-0" data-testid="sights-map-legend">
      <span class="pin pin-must d-inline-flex" style="width:18px;height:18px;font-size:.65rem" aria-hidden="true"><Icon name="temple" :size="12" /></span> Square = Must visit ·
      <span class="pin pin-nice d-inline-flex" style="width:18px;height:18px;font-size:.65rem" aria-hidden="true"><Icon name="temple" :size="12" /></span> Circle = Include if it fits · the icon is the theme · "Not interested" sights have no pin
    </p>
  </div>
</template>
