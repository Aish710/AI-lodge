<script setup>
// A day's stop marker in lists and legends: cloud (day 1), star (day 2), heart (day 3), triangle (day 4), each with the stop number.
import { h } from 'vue'
import { SHAPE_PATHS, dayColor, dayShape } from '../lib/mapstyle.js'
const props = defineProps({ day: { type: Number, required: true }, num: { type: [Number, String], default: null }, size: { type: Number, default: 30 } })
const render = () => {
  const shape = dayShape(props.day)
  const kids = []
  if (SHAPE_PATHS[shape]) {
    const inner = [h('path', { d: SHAPE_PATHS[shape], fill: dayColor(props.day), stroke: '#2d1566', 'stroke-width': 1.6, 'stroke-linejoin': 'round' })]
    if (props.num !== null) inner.push(h('text', { x: 12, y: 14.6, 'text-anchor': 'middle', 'font-size': 8.5, 'font-weight': 800, fill: '#fff', stroke: '#2d1566', 'stroke-width': 0.6, 'paint-order': 'stroke' }, String(props.num)))
    kids.push(h('svg', { class: 'shape-svg', viewBox: '0 0 24 24', 'aria-hidden': 'true', focusable: 'false' }, inner))
  } else if (props.num !== null) kids.push(h('span', { class: 'shape-num' }, String(props.num)))
  return h('span', { class: ['marker', `shape-${shape}`], style: { '--day': dayColor(props.day), width: `${props.size}px`, height: `${props.size}px` }, 'aria-hidden': 'true' }, kids)
}
</script>
<template><render /></template>
