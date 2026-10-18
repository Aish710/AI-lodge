// Per-day marker styling shared by the map and the timeline. Colour AND shape AND number: status is never conveyed by colour alone.
export const DAY_COLORS = ['#1c6b66', '#b83a26', '#4a3f9f', '#7a4e00', '#25608f', '#7a2e6e', '#3d6b1f']
export const DAY_SHAPES = ['cloud', 'star', 'heart', 'triangle']
// Outline paths (24x24) for the three drawn shapes; the fourth (triangle) stays a CSS clip-path. Shape + number + colour: never colour alone.
export const SHAPE_PATHS = {
  cloud: 'M7 19a4.5 4.5 0 0 1-.9-8.9A6 6 0 0 1 17.5 9.2 4.7 4.7 0 0 1 17 19z',
  star: 'M12 2.5l2.9 6.2 6.8.8-5 4.7 1.3 6.7L12 17.5l-6 3.4 1.3-6.7-5-4.7 6.8-.8z',
  heart: 'M12 21s-9-5.6-9-12a5 5 0 0 1 9-3 5 5 0 0 1 9 3c0 6.4-9 12-9 12z',
}
/** SVG string for a Leaflet marker (static, built from constants and a colour from DAY_COLORS only). */
export const shapeSvg = (shape, color, num = null) => {
  if (!SHAPE_PATHS[shape]) return ''
  const text = num === null ? '' : `<text x="12" y="14.6" text-anchor="middle" font-size="8.5" font-weight="800" fill="#fff" stroke="#2d1566" stroke-width=".6" paint-order="stroke">${Number(num)}</text>`
  return `<svg class="shape-svg" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="${SHAPE_PATHS[shape]}" fill="${color}" stroke="#2d1566" stroke-width="1.6" stroke-linejoin="round"/>${text}</svg>`
}
export const dayColor = (day) => DAY_COLORS[(day - 1) % DAY_COLORS.length]
export const dayShape = (day) => DAY_SHAPES[(day - 1) % DAY_SHAPES.length]
export const shapeName = (day) => dayShape(day)
