<script setup>
// Renders the blocks of a generated markdown file (headings, paragraphs, tables, lists) as plain text. Nothing is interpreted as HTML.
defineProps({ blocks: { type: Array, required: true } })
</script>
<template>
  <template v-for="(b, i) in blocks" :key="i">
    <h3 v-if="b.type === 'h'" class="h6 mt-2">{{ b.text }}</h3>
    <p v-else-if="b.type === 'p'" class="small">{{ b.text }}</p>
    <div v-else-if="b.type === 'table'" class="table-responsive"><table class="table table-honest"><thead><tr><th v-for="h in b.head" :key="h" scope="col">{{ h }}</th></tr></thead><tbody><tr v-for="(row, j) in b.rows" :key="j"><td v-for="(c, k) in row" :key="k">{{ c }}</td></tr></tbody></table></div>
    <ul v-else-if="b.type === 'ul'" class="small"><li v-for="x in b.items" :key="x">{{ x }}</li></ul>
  </template>
</template>
