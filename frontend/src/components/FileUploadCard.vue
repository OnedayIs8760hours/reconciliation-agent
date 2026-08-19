<script setup lang="ts">
import { computed, ref } from 'vue'
import { CheckCircle2, FileSpreadsheet, UploadCloud, AlertTriangle } from '@lucide/vue'
import type { UploadedFileInfo } from '@/types/reconciliation'

const props = defineProps<{
  label: string
  description: string
  file: UploadedFileInfo
  variant: 'a' | 'b'
}>()

const emit = defineEmits<{
  change: [variant: 'a' | 'b', file: File]
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const hasFile = computed(() => props.file.uploaded && props.file.name)

function openFilePicker() {
  fileInput.value?.click()
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  emit('change', props.variant, file)
  input.value = ''
}
</script>

<template>
  <section class="file-card panel-card">
    <div class="section-kicker">{{ label }}</div>
    <p class="muted">{{ description }}</p>

    <input ref="fileInput" class="sr-only" type="file" accept=".xlsx" @change="handleFileChange" />

    <button v-if="!hasFile" class="upload-dropzone" type="button" @click="openFilePicker">
      <UploadCloud :size="30" />
      <span>拖拽 Excel 到这里</span>
      <small>或点击上传</small>
    </button>

    <div v-else class="uploaded-card">
      <div class="uploaded-icon"><FileSpreadsheet :size="26" /></div>
      <div class="uploaded-body">
        <strong>{{ file.name }}</strong>
        <span>{{ file.size }}</span>
        <div class="upload-status success"><CheckCircle2 :size="16" /> 已选择</div>
        <div v-if="file.recognized" class="upload-status success"><CheckCircle2 :size="16" /> 已识别为系统出入库表</div>
        <div v-if="file.warning" class="upload-status warning"><AlertTriangle :size="16" /> {{ file.warning }}</div>
      </div>
      <button class="text-button" type="button" @click="openFilePicker">更换</button>
    </div>
  </section>
</template>
