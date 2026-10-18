<script setup>
// Inline SVG icons with 2-3px ink strokes (bodies live in lib/icons.js, as simple self-closing tags). Built as elements with h(), with no raw HTML.
// Decorative: always aria-hidden; the text next to an icon carries the meaning.
import { computed, h } from 'vue'
import { ICONS } from '../lib/icons.js'
const props = defineProps({ name: { type: String, required: true }, size: { type: Number, default: 18 } })
const parts = computed(() => [...(ICONS[props.name] ?? '').matchAll(/<(\w+)([^>]*?)\/?>/g)].map((m) => [m[1], Object.fromEntries([...m[2].matchAll(/([\w-]+)="([^"]*)"/g)].map((a) => [a[1], a[2]]))]))
const render = () => h('svg', { class: 'ico', width: props.size, height: props.size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 2.5, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true', focusable: 'false' }, parts.value.map(([tag, attrs]) => h(tag, attrs)))
</script>
<template><render /></template>
<style>.ico { flex: none; vertical-align: -3px; }</style>
