// Tiny Markdown readers for the generated evidence files. Output is always PLAIN TEXT (rendered with interpolation, never as HTML).
export const plain = (t) => String(t ?? '').replace(/\*\*/g, '').replace(/`/g, '').replace(/\[([^\]]+)\]\([^)]+\)/g, '$1').replace(/\*([^*]+)\*/g, '$1').trim()

const cells = (line) => line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim())
const isSep = (line) => /^\s*\|[\s:|-]+\|?\s*$/.test(line) && line.includes('-')

/** Markdown -> blocks: {type:'h', level, text} | {type:'p', text} | {type:'ul', items} | {type:'table', head, rows}. */
export function parseBlocks(md) {
  const lines = String(md ?? '').split('\n')
  const out = []
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (!line.trim()) continue
    const h = /^(#{1,6})\s+(.*)$/.exec(line)
    if (h) { out.push({ type: 'h', level: h[1].length, text: plain(h[2]) }); continue }
    if (line.trim().startsWith('|') && lines[i + 1] && isSep(lines[i + 1])) {
      const head = cells(line).map(plain)
      const rows = []
      i += 2
      while (i < lines.length && lines[i].trim().startsWith('|')) { rows.push(cells(lines[i]).map(plain)); i++ }
      i--
      out.push({ type: 'table', head, rows })
      continue
    }
    if (/^\s*[-*]\s+/.test(line)) {
      const items = []
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) { items.push(plain(lines[i].replace(/^\s*[-*]\s+/, ''))); i++ }
      i--
      out.push({ type: 'ul', items })
      continue
    }
    out.push({ type: 'p', text: plain(line) })
  }
  return out
}

/** SAFETY_LOG: every table row whose first cell is a number -> {n, risk, safeguard, test, status}. */
export function parseRiskTable(md) {
  const rows = []
  for (const line of String(md ?? '').split('\n')) {
    if (!line.trim().startsWith('|')) continue
    const c = cells(line)
    if (c.length >= 5 && /^\d+$/.test(c[0])) rows.push({ n: Number(c[0]), risk: plain(c[1]), safeguard: plain(c[2]), test: plain(c[3]), status: plain(c.slice(4).join(' | ')) })
  }
  return rows
}

/** README-claims.md: "- **id**: sentence" -> [{id, text}] with the sentence kept verbatim. */
export function parseClaims(md) {
  return String(md ?? '').split('\n').map((l) => /^-\s+\*\*([^*]+)\*\*:\s+(.*)$/.exec(l)).filter(Boolean).map((m) => ({ id: m[1], text: m[2].trim() }))
}

/** Bullets under a "## heading" (used for WHAT THESE NUMBERS DO NOT SHOW). */
export function sectionBullets(md, heading) {
  const lines = String(md ?? '').split('\n')
  const start = lines.findIndex((l) => l.startsWith('## ') && l.toUpperCase().includes(heading.toUpperCase()))
  if (start < 0) return []
  const out = []
  for (let i = start + 1; i < lines.length && !lines[i].startsWith('## '); i++) if (/^\s*-\s+/.test(lines[i])) out.push(plain(lines[i].replace(/^\s*-\s+/, '')))
  return out
}

/** tests/results/*.md header: "Passed: N, failed: M, skipped: S, total: T". */
export function testSummary(md) {
  const m = /Passed:\s*(\d+),\s*failed:\s*(\d+)(?:,\s*skipped:\s*(\d+))?,\s*total:\s*(\d+)/.exec(String(md ?? ''))
  const when = /Generated\s+([0-9: \-A-Z]+?)\s+by/.exec(String(md ?? ''))
  const type = /Run type:\s*(.+?)\./.exec(String(md ?? ''))
  const rev = /Git revision:\s*(.+?)\./.exec(String(md ?? ''))
  return m ? { passed: Number(m[1]), failed: Number(m[2]), skipped: Number(m[3] ?? 0), total: Number(m[4]), generated: when?.[1] ?? null,
    runType: type?.[1] ?? null, revision: rev?.[1] ?? null } : null
}
export const vitestSummary = (j) => (j && typeof j.numTotalTests === 'number' ? { passed: j.numPassedTests, failed: j.numFailedTests, total: j.numTotalTests } : null)
export const playwrightSummary = (j) => (j?.stats ? { passed: j.stats.expected, failed: j.stats.unexpected + (j.stats.flaky ?? 0), total: j.stats.expected + j.stats.unexpected + (j.stats.skipped ?? 0) + (j.stats.flaky ?? 0) } : null)

/** Number of participants in the user-test results CSV: data rows with at least one non-empty cell (the header row is not counted). */
export function countUserTestRows(csv) {
  const lines = String(csv ?? '').split(/\r?\n/).filter((l) => l.trim())
  return lines.slice(1).filter((l) => l.split(',').some((c) => c.trim())).length
}
