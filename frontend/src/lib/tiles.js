// Base-map tiles with a graceful fallback. OpenStreetMap answers a request it rejects (no Referer, rate limit) with HTTP 403 and a PICTURE
// saying "Access blocked". An <img> shows that picture and fires no error event, so the tiles alone cannot tell us. A single small probe
// request for the world tile (read with CORS, which OSM allows) does: the tile layer is added only if the probe says the server is serving us.
// If not, the map keeps its pins on a plain background and the page shows a small note. Slow answers are not treated as failure.
import L from 'leaflet'

export const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
export const PROBE_URL = 'https://tile.openstreetmap.org/0/0/0.png'
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors'
const OK_FOR_MS = 10 * 60_000
const BAD_FOR_MS = 60_000
let memo = null

/** true = the tile server is serving us (or we could not tell in time); false = it refused us or could not be reached. */
export async function tilesAvailable({ fetchImpl = (...a) => fetch(...a), now = () => Date.now(), timeoutMs = 4000, force = false } = {}) {
  if (!force && memo && now() - memo.at < (memo.ok ? OK_FOR_MS : BAD_FOR_MS)) return memo.ok
  const controller = new AbortController()
  let slow = false
  const timer = setTimeout(() => { slow = true; controller.abort() }, timeoutMs)
  let ok
  try {
    const res = await fetchImpl(PROBE_URL, { mode: 'cors', credentials: 'omit', cache: 'force-cache', referrerPolicy: 'origin', signal: controller.signal })
    ok = res.ok
  } catch {
    ok = slow // a timeout is "unknown": keep the tiles. A refusal or a network error is not.
  } finally { clearTimeout(timer) }
  memo = { ok, at: now() }
  return ok
}
export function resetTileProbe() { memo = null }

/** Adds the OpenStreetMap layer once the probe passes. Calls onUnavailable() instead when it does not, or when the tiles then fail to load. */
export function attachBaseLayer(map, { onUnavailable = () => {}, probe = tilesAvailable } = {}) {
  let layer = null
  let gone = false
  const giveUp = () => { if (layer) { map.removeLayer(layer); layer = null } if (!gone) { gone = true; onUnavailable() } }
  probe().then((ok) => {
    if (!ok) return giveUp()
    if (!map._container || gone) return
    let loads = 0
    let errors = 0
    layer = L.tileLayer(TILE_URL, {
      // The page sends no Referer (privacy), but OpenStreetMap's tile servers block requests without one. Only the tile images send the bare origin (no path, no query).
      referrerPolicy: 'origin', maxZoom: 18, attribution: ATTRIBUTION,
    })
    layer.on('tileload', () => { loads += 1 })
    layer.on('tileerror', () => { errors += 1; if (errors >= 3 && loads === 0) giveUp() })
    layer.addTo(map)
  }).catch(giveUp)
  return { dispose() { gone = true } }
}
