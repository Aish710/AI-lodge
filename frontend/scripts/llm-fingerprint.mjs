// The same hash as backend/scripts/live_common.py llm_fingerprint(): sha256 over backend/app/llm (*.py and *.json, sorted by relative path, CRLF normalised).
import { createHash } from 'node:crypto'
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative, sep } from 'node:path'

function walk(dir) {
  const out = []
  for (const n of readdirSync(dir)) {
    const p = join(dir, n)
    if (statSync(p).isDirectory()) { if (n !== '__pycache__') out.push(...walk(p)) } else if (/\.(py|json)$/.test(n)) out.push(p)
  }
  return out
}

export function llmFingerprint(root) {
  const dir = join(root, 'backend', 'app', 'llm')
  if (!existsSync(dir)) return null
  const h = createHash('sha256')
  const files = walk(dir).map((p) => [relative(dir, p).split(sep).join('/'), p]).sort((a, b) => (Buffer.from(a[0]).compare(Buffer.from(b[0]))))
  for (const [rel, p] of files) {
    const body = readFileSync(p).toString('latin1').replace(/\r\n/g, '\n')
    h.update(Buffer.concat([Buffer.from(rel + '\n'), Buffer.from(body, 'latin1'), Buffer.from('\n--\n')]))
  }
  return h.digest('hex').slice(0, 12)
}
