// Writes the static-host config next to the build: _headers (security headers + CSP) and _redirects (single-page-app rewrite).
// Format verified against the Netlify docs: a `_headers` file in the publish directory; `/*  /index.html  200` for the SPA rewrite.
// The CSP allows only this site, the OpenStreetMap tile server (tile images, and the single probe request that decides whether to show them) and the configured API origin (VITE_API_BASE_URL).
// Usage: node scripts/write-host-config.mjs [outDir=dist]     (runs automatically after `npm run build`)
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

export function apiOrigin(value) {
  if (!value) return null
  try { return new URL(value).origin } catch { return null }
}

export function headersFile(api) {
  const connect = ["'self'", api, 'https://tile.openstreetmap.org'].filter(Boolean).join(' ')  // the tile server is also read once by the map's availability probe
  const csp = [
    "default-src 'self'", "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",               // Leaflet and Vue set inline style attributes; scripts stay locked to 'self'
    "img-src 'self' data: https://tile.openstreetmap.org", "font-src 'self'", `connect-src ${connect}`,
    "base-uri 'self'", "form-action 'self'", "frame-ancestors 'none'", "object-src 'none'",
  ].join('; ')
  return `/*\n  Content-Security-Policy: ${csp}\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: no-referrer\n  X-Frame-Options: DENY\n  Permissions-Policy: geolocation=(), camera=(), microphone=()\n\n/assets/*\n  Cache-Control: public, max-age=31536000, immutable\n`
}

export const REDIRECTS = '/*  /index.html  200\n'

export function writeHostConfig({ outDir, apiBase }) {
  const api = apiOrigin(apiBase)
  writeFileSync(join(outDir, '_headers'), headersFile(api))
  writeFileSync(join(outDir, '_redirects'), REDIRECTS)
  return { api }
}

function envFromFile(root) {
  const f = join(root, '.env')
  if (!existsSync(f)) return null
  const m = /^VITE_API_BASE_URL=(.*)$/m.exec(readFileSync(f, 'utf8'))
  return m ? m[1].trim() : null
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  const root = resolve(import.meta.dirname, '..')
  const outDir = resolve(root, process.argv[2] ?? 'dist')
  const apiBase = process.env.VITE_API_BASE_URL ?? envFromFile(root)
  const { api } = writeHostConfig({ outDir, apiBase })
  if (!api) console.warn('WARNING: VITE_API_BASE_URL is not set, so the CSP only allows this site: the app cannot reach the API. Set it for the build.')
  else console.log(`host config written to ${outDir} (API origin allowed by CSP: ${api})`)
}
