<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import FileUploadCard from '@/components/FileUploadCard.vue'
import ReconciliationSettings from '@/components/ReconciliationSettings.vue'
import TaskProgress from '@/components/TaskProgress.vue'
import VerifySummary from '@/components/VerifySummary.vue'
import CoverageStatistics from '@/components/CoverageStatistics.vue'
import ResultDownload from '@/components/ResultDownload.vue'
import ExceptionDrawer from '@/components/ExceptionDrawer.vue'
import { initialTask, successfulTask } from '@/api/reconciliation'
import type { ReconciliationTask } from '@/types/reconciliation'

const task = reactive<ReconciliationTask>(structuredClone(initialTask))
const month = ref('2026-07')
const running = ref(false)
const drawerOpen = ref(false)

const canStart = computed(() => Boolean(task.aFile.uploaded && task.bFile.uploaded && month.value))

function changeFile(variant: 'a' | 'b') {
  if (variant === 'a') {
    task.aFile = {
      name: '2026年7月玖鸣对账单.xlsx',
      size: '1.8 MB',
      uploaded: true,
    }
    return
  }

  task.bFile = {
    name: '台州市川跃家居用品有限公司.xlsx',
    size: '3.2 MB',
    uploaded: true,
    recognized: true,
  }
}

function applyTask(nextTask: ReconciliationTask) {
  Object.assign(task, structuredClone(nextTask))
}

function startReconciliation() {
  if (!canStart.value || running.value) return

  running.value = true
  task.status = 'MATCHING'
  task.title = '玖鸣 · 2026年7月对账'
  task.progressSteps = [
    { id: 1, title: '文件检查', status: 'done' },
    { id: 2, title: '生成 C 表底稿', status: 'done' },
    { id: 3, title: 'A/B 数据匹配', status: 'active' },
    { id: 4, title: 'B 表反向核查', status: 'pending' },
    { id: 5, title: '最终验收', status: 'pending' },
  ]
  task.progressDetail = {
    currentText: '正在匹配 B 表',
    progress: 72,
    processedCRecords: 328,
    totalCRecords: 541,
    matchedBRecords: 402,
    manualReviewCount: 17,
  }

  window.setTimeout(() => {
    applyTask(successfulTask)
    running.value = false
  }, 900)
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
