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
import type { ExcelSheetPreview, ExcelLlmAnalysisResult, ProductMappingResponse } from '@/api/reconciliation'
import type { ReconciliationTask } from '@/types/reconciliation'

const task = reactive<ReconciliationTask>(structuredClone(initialTask))
const month = ref('2026-07')
const running = ref(false)
const drawerOpen = ref(false)
const aFileObject = ref<File | null>(null)
const bFileObject = ref<File | null>(null)
const uploadError = ref('')
const aPreview = ref<ExcelSheetPreview | null>(null)
const llmAnalysis = ref<ExcelLlmAnalysisResult | null>(null)
const productMapping = ref<ProductMappingResponse | null>(null)

const canStart = computed(() => Boolean(aFileObject.value && bFileObject.value && month.value && !running.value))

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
    task.title = `${response.task_id} · A表已完成 LLM 行数分析`
    task.month = month.value
    aPreview.value = response.a_preview
    llmAnalysis.value = response.llm_result
    productMapping.value = response.product_mapping
    task.progressSteps = initialTask.progressSteps.map((step) => ({ ...step }))
    task.progressDetail = {
      currentText: `LLM 判断 A 表数据行数：${response.llm_result.row_count_guess ?? '未能确定'}`,
      progress: 20,
      processedCRecords: 0,
      totalCRecords: Number(response.llm_result.row_count_guess) || 0,
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

      <section v-if="aPreview && llmAnalysis" class="panel-card upload-result-card">
        <div class="upload-status success">A 表 LLM 预览分析完成</div>
        <p class="muted small">Sheet：{{ aPreview.sheet_name }} ｜ 最大行数：{{ aPreview.max_row }} ｜ 最大列数：{{ aPreview.max_column }}</p>
        <p class="muted small">LLM 估算行数：{{ llmAnalysis.row_count_guess ?? '未能确定' }}</p>
        <p class="muted small">置信度：{{ llmAnalysis.confidence ?? '-' }}</p>
        <p class="muted small">原因：{{ llmAnalysis.reason ?? llmAnalysis.raw_text ?? '-' }}</p>
      </section>

      <section v-if="productMapping" class="panel-card upload-result-card">
        <div class="upload-status success">商品规格映射完成</div>
        <p class="muted small">A列字段：{{ productMapping.a_column_name }} ｜ B列字段：{{ productMapping.b_column_name }}</p>
        <p class="muted small">A字段识别：第 {{ productMapping.structure.a_sheet.header_row_guess }} 行表头 ｜ 置信度 {{ productMapping.structure.a_sheet.confidence }}</p>
        <p class="muted small">B字段识别：第 {{ productMapping.structure.b_sheet.header_row_guess }} 行表头 ｜ 置信度 {{ productMapping.structure.b_sheet.confidence }}</p>
        <p class="muted small">A去重数量：{{ productMapping.summary.a_unique_count }} ｜ B去重数量：{{ productMapping.summary.b_unique_count }}</p>
        <p class="muted small">成功映射：{{ productMapping.summary.mapping_count }} ｜ 待复核：{{ productMapping.summary.need_review_count }}</p>
        <p class="muted small">A未匹配：{{ productMapping.summary.unmatched_a_count }} ｜ B未匹配：{{ productMapping.summary.unmatched_b_count }}</p>
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
