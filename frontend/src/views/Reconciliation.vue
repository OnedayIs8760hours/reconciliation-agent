<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import FileUploadCard from '@/components/FileUploadCard.vue'
import ReconciliationSettings from '@/components/ReconciliationSettings.vue'
import TaskProgress from '@/components/TaskProgress.vue'
import VerifySummary from '@/components/VerifySummary.vue'
import CoverageStatistics from '@/components/CoverageStatistics.vue'
import ResultDownload from '@/components/ResultDownload.vue'
import ExceptionDrawer from '@/components/ExceptionDrawer.vue'
import { initialTask, uploadReconciliationFiles } from '@/api/reconciliation'
import type { ReconciliationTask } from '@/types/reconciliation'

const task = reactive<ReconciliationTask>(structuredClone(initialTask))
const month = ref('2026-07')
const running = ref(false)
const drawerOpen = ref(false)
const aFileObject = ref<File | null>(null)
const bFileObject = ref<File | null>(null)
const uploadError = ref('')

const canStart = computed(() => Boolean(aFileObject.value && bFileObject.value && month.value && !running.value))
const hasCreatedTask = computed(() => task.id !== initialTask.id)

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function changeFile(variant: 'a' | 'b', file: File) {
  uploadError.value = ''

  if (variant === 'a') {
    aFileObject.value = file
    task.aFile = {
      name: file.name,
      size: formatFileSize(file.size),
      uploaded: true,
    }
    return
  }

  const recognized = file.name.startsWith('台州')
  bFileObject.value = file
  task.bFile = {
    name: file.name,
    size: formatFileSize(file.size),
    uploaded: true,
    recognized,
    warning: recognized ? undefined : 'B表文件名通常以“台州”开头，请确认是否为系统出入库明细',
  }
}

async function startReconciliation() {
  if (!canStart.value || !aFileObject.value || !bFileObject.value) return

  running.value = true
  uploadError.value = ''
  task.status = 'PROCESSING'
  task.title = '正在上传对账文件'
  task.progressDetail = {
    ...task.progressDetail,
    currentText: '正在上传 A 表和 B 表',
    progress: 5,
  }

  try {
    const response = await uploadReconciliationFiles(aFileObject.value, bFileObject.value)

    task.id = response.task_id
    task.status = response.status
    task.title = `${response.task_id} · 文件已上传`
    task.month = month.value
    task.progressSteps = initialTask.progressSteps.map((step) => ({ ...step }))
    task.progressDetail = {
      currentText: '文件上传完成，等待开始对账接口',
      progress: 10,
      processedCRecords: 0,
      totalCRecords: 0,
      matchedBRecords: 0,
      manualReviewCount: 0,
    }
  } catch (error) {
    task.status = 'FAILED'
    task.title = '文件上传失败'
    uploadError.value = error instanceof Error ? error.message : '上传失败，请稍后重试'
    task.progressDetail = {
      ...task.progressDetail,
      currentText: uploadError.value,
      progress: 0,
    }
  } finally {
    running.value = false
  }
}
</script>

<template>
  <div class="workspace">
    <aside class="input-panel">
      <div class="panel-title">
        <span>① 对账文件</span>
        <strong>输入区</strong>
      </div>
      <FileUploadCard
        label="A表 / 业务对账单"
        description="上传业务侧原始对账文件。"
        :file="task.aFile"
        variant="a"
        @change="changeFile"
      />
      <FileUploadCard
        label="B表 / 系统出入库明细"
        description="上传系统出入库记录，用于本月反向核查。"
        :file="task.bFile"
        variant="b"
        @change="changeFile"
      />
      <ReconciliationSettings v-model:month="month" :can-start="canStart" :running="running" @start="startReconciliation" />

      <section v-if="uploadError || hasCreatedTask" class="panel-card upload-result-card">
        <div v-if="hasCreatedTask" class="upload-status success">任务已创建：{{ task.id }}</div>
        <div v-if="uploadError" class="upload-status warning">{{ uploadError }}</div>
        <p class="muted small">当前仅完成上传建档；完整对账会在后续接入运行接口。</p>
      </section>
    </aside>

    <main class="result-panel">
      <TaskProgress :title="task.title" :steps="task.progressSteps" :detail="task.progressDetail" />
      <VerifySummary :metrics="task.verifyMetrics" :status="task.status" />
      <CoverageStatistics :coverage="task.coverage" />
      <section class="exception-summary result-card">
        <div>
          <span class="section-kicker">异常明细</span>
          <h2>{{ task.exceptions.length ? `${task.exceptions.length} 条需要复核` : '暂无异常记录' }}</h2>
        </div>
        <button class="ghost-button" type="button" :disabled="!task.exceptions.length" @click="drawerOpen = true">查看异常明细</button>
      </section>
      <ResultDownload :files="task.downloads" :status="task.status" />
    </main>

    <ExceptionDrawer :open="drawerOpen" :records="task.exceptions" @close="drawerOpen = false" />
  </div>
</template>
