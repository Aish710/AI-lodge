// Per-day marker styling shared by the map and the timeline. Colour AND shape AND number: status is never conveyed by colour alone.
export const DAY_COLORS = ['#1c6b66', '#b83a26', '#4a3f9f', '#7a4e00', '#25608f', '#7a2e6e', '#3d6b1f']
export const DAY_SHAPES = ['circle', 'square', 'diamond', 'triangle']
export const dayColor = (day) => DAY_COLORS[(day - 1) % DAY_COLORS.length]
export const dayShape = (day) => DAY_SHAPES[(day - 1) % DAY_SHAPES.length]
export const shapeName = (day) => dayShape(day)
