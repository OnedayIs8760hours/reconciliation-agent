<script setup lang="ts">
import { FileDown, FileSpreadsheet, FileText } from '@lucide/vue'
import type { DownloadFile, TaskStatus } from '@/types/reconciliation'

const props = defineProps<{
  files: DownloadFile[]
  status: TaskStatus
  taskId?: string
}>()

const emit = defineEmits<{
  download: [file: DownloadFile]
}>()

function requestDownload(file: DownloadFile) {
  if (!file.enabled) return
  emit('download', file)
}
</script>

<template>
  <section class="download-card result-card">
    <span class="section-kicker">生成文件</span>
    <div class="download-list">
      <article v-for="file in files" :key="file.id" class="download-item">
        <component :is="file.type === 'excel' ? FileSpreadsheet : FileText" :size="22" />
        <span>{{ file.name }}</span>
        <button type="button" :disabled="!file.enabled" @click="requestDownload(file)">
          <FileDown :size="16" /> 下载
        </button>
      </article>
    </div>
    <p v-if="status !== 'SUCCESS'" class="muted small">只有核查通过后，才开放 C 表与核查报告下载。</p>
  </section>
</template>
