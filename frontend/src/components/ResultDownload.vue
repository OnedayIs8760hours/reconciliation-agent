<script setup lang="ts">
import { FileDown, FileSpreadsheet, FileText } from '@lucide/vue'
import type { DownloadFile, TaskStatus } from '@/types/reconciliation'

const props = defineProps<{
  files: DownloadFile[]
  status: TaskStatus
}>()

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

function openDownload(file: DownloadFile) {
  if (!file.enabled || !file.url) return
  window.open(`${API_BASE_URL}${file.url}`, '_blank')
}

function hintText(status: TaskStatus) {
  if (status === 'SUCCESS') return '核查通过，C 表、B 标注表和核查报告均可下载。'
  if (status === 'FAILED') return '核查未通过，仍可下载已生成文件和核查报告用于排查。'
  return '任务完成后会开放结果文件下载。'
}

function buttonText(file: DownloadFile) {
  if (!file.enabled) return '未生成'
  return '下载'
}

function ariaLabel(file: DownloadFile) {
  return `${buttonText(file)}${file.name}`
}

function isDownloadDisabled(file: DownloadFile) {
  return !file.enabled || !file.url
}
</script>

<template>
  <section class="download-card result-card">
    <span class="section-kicker">生成文件</span>
    <div class="download-list">
      <article v-for="file in files" :key="file.id" class="download-item">
        <component :is="file.type === 'excel' ? FileSpreadsheet : FileText" :size="22" />
        <span>{{ file.name }}</span>
        <button type="button" :disabled="isDownloadDisabled(file)" :aria-label="ariaLabel(file)" @click="openDownload(file)">
          <FileDown :size="16" /> {{ buttonText(file) }}
        </button>
      </article>
    </div>
    <p class="muted small">{{ hintText(props.status) }}</p>
  </section>
</template>
