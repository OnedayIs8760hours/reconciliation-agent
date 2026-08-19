<script setup lang="ts">
import { computed } from 'vue'
import { CheckCircle2, FileSpreadsheet, UploadCloud, AlertTriangle } from '@lucide/vue'
import type { UploadedFileInfo } from '@/types/reconciliation'

const props = defineProps<{
  label: string
  description: string
  file: UploadedFileInfo
  variant: 'a' | 'b'
}>()

const emit = defineEmits<{
  change: [variant: 'a' | 'b']
}>()

const hasFile = computed(() => props.file.uploaded && props.file.name)
</script>

<template>
  <section class="file-card panel-card">
    <div class="section-kicker">{{ label }}</div>
    <p class="muted">{{ description }}</p>

    <button v-if="!hasFile" class="upload-dropzone" type="button" @click="emit('change', variant)">
      <UploadCloud :size="30" />
      <span>拖拽 Excel 到这里</span>
      <small>或点击上传</small>
    </button>

    <div v-else class="uploaded-card">
      <div class="uploaded-icon"><FileSpreadsheet :size="26" /></div>
      <div class="uploaded-body">
        <strong>{{ file.name }}</strong>
        <span>{{ file.size }}</span>
        <div class="upload-status success"><CheckCircle2 :size="16" /> 已上传</div>
        <div v-if="file.recognized" class="upload-status success"><CheckCircle2 :size="16" /> 已识别为系统出入库表</div>
        <div v-if="file.warning" class="upload-status warning"><AlertTriangle :size="16" /> {{ file.warning }}</div>
      </div>
      <button class="text-button" type="button" @click="emit('change', variant)">更换</button>
    </div>
  </section>
</template>
