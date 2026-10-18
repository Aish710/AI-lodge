// Inline SVG icon bodies (24x24 viewBox, drawn with a 2.5px stroke in currentColor). Decorative: always rendered aria-hidden.
export const ICONS = {
  tram: '<rect x="4" y="3" width="16" height="14" rx="3" fill="#7be3e8"/><path d="M4 11h16M8 21l2-4M16 21l-2-4M9 7h.01M15 7h.01"/>',
  house: '<path d="M3 11l9-8 9 8v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" fill="#c7b8ff"/><path d="M10 21v-6h4v6"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2" fill="#fff3a8"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7"/>',
  warn: '<path d="M12 3l10 18H2z" fill="#ffd6a5"/><path d="M12 10v5M12 18h.01"/>',
  star: '<path d="M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6L3.3 9.3l6.1-.7z" fill="#fff3a8"/>',
  sparkle: '<path d="M12 2l2.2 7.8L22 12l-7.8 2.2L12 22l-2.2-7.8L2 12l7.8-2.2z" fill="#fff"/>',
  cloud: '<path d="M7 18a4 4 0 0 1-.6-7.96A5.5 5.5 0 0 1 17 9.5a4.2 4.2 0 0 1 .5 8.5z" fill="#fff"/>',
  heart: '<path d="M12 20s-8-5-8-11a4.5 4.5 0 0 1 8-2.5A4.5 4.5 0 0 1 20 9c0 6-8 11-8 11z" fill="#f09fe0"/>',
  temple: '<path d="M3 9l9-5 9 5z" fill="#ffd6a5"/><path d="M5 10v9M10 10v9M14 10v9M19 10v9M3 20h18"/>',
  bag: '<path d="M5 8h14l-1 12H6z" fill="#f6b8ea"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',
  bowl: '<path d="M3 11h18a9 8 0 0 1-18 0z" fill="#ffd6a5"/><path d="M9 3l-1 5M14 3l-1 5M8 20h8"/>',
  map: '<path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z" fill="#b5ead7"/><path d="M9 4v14M15 6v14"/>',
  ticket: '<path d="M3 8a2 2 0 0 0 0 4v4h18v-4a2 2 0 0 1 0-4V6H3z" fill="#ffd6a5" transform="translate(0 1)"/><path d="M14 7v10" stroke-dasharray="2 2.5"/>',
  pin: '<path d="M12 21s-7-6-7-11a7 7 0 0 1 14 0c0 5-7 11-7 11z" fill="#f6b8ea"/><circle cx="12" cy="10" r="2.5"/>',
}
export const iconSvg = (name, size = 18) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="#2d1566" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${ICONS[name] ?? ''}</svg>`
