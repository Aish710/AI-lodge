<script setup>
// Modal confirmation on a native <dialog>: focus is trapped, Esc cancels, and focus returns to the control that opened it.
import { nextTick, ref, watch } from 'vue'
const props = defineProps({ open: Boolean, title: { type: String, required: true }, confirmLabel: { type: String, default: 'Confirm' }, cancelLabel: { type: String, default: 'Cancel' } })
const emit = defineEmits(['confirm', 'cancel'])
const el = ref(null)
watch(() => props.open, async (v) => {
  await nextTick()
  const d = el.value
  if (!d) return
  if (v && !d.open) { d.showModal ? d.showModal() : d.setAttribute('open', '') }
  if (!v && d.open) { d.close ? d.close() : d.removeAttribute('open') }
})
</script>
<template>
  <dialog ref="el" class="confirm-dialog" :aria-labelledby="'dlg-title'" @cancel.prevent="emit('cancel')" data-testid="confirm-dialog">
    <h2 id="dlg-title" class="h5">{{ title }}</h2>
    <div class="mb-3"><slot /></div>
    <div class="d-flex flex-wrap gap-2 justify-content-end">
      <button type="button" class="btn btn-outline-secondary" autofocus @click="emit('cancel')" data-testid="dialog-cancel">{{ cancelLabel }}</button>
      <button type="button" class="btn btn-primary" @click="emit('confirm')" data-testid="dialog-confirm">{{ confirmLabel }}</button>
    </div>
  </dialog>
</template>
