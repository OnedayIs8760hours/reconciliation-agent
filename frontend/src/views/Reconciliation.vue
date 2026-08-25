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
import type { ExcelSheetPreview, ExcelLlmAnalysisResult, ProductMappingResponse, UploadReconciliationResponse } from '@/api/reconciliation'
import type { DownloadFile, ExceptionRecord, ProgressStep, ReconciliationTask, TaskStatus, VerifyMetric } from '@/types/reconciliation'

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

function formatJson(value: unknown) {
  return JSON.stringify(value, null, 2)
}

function getProgressSteps(status: TaskStatus): ProgressStep[] {
  const finalStatus: ProgressStep['status'] = status === 'SUCCESS' ? 'done' : 'failed'
  return [
    { id: 1, title: '文件检查', status: 'done' as const },
    { id: 2, title: '生成 C 表底稿', status: 'done' as const },
    { id: 3, title: 'A/B 数据匹配', status: 'done' as const },
    { id: 4, title: 'B 表反向核查', status: 'done' as const },
    { id: 5, title: '最终验收', status: finalStatus },
  ]
}

function buildVerifyMetrics(response: UploadReconciliationResponse): VerifyMetric[] {
  if (!response.verify_report?.items?.length) {
    return initialTask.verifyMetrics.map((metric) => ({ ...metric }))
  }

  return response.verify_report.items.map((item) => ({
    label: item.name,
    value: formatMetricValue(item.value),
    passed: item.passed,
    hint: item.message,
  }))
}

function formatMetricValue(value: unknown): string | number {
  if (typeof value === 'number') return value
  if (typeof value === 'string') return value
  if (value === null || value === undefined) return '-'
  return JSON.stringify(value)
}

function buildExceptions(response: UploadReconciliationResponse): ExceptionRecord[] {
  if (!Array.isArray(response.exceptions)) return []

  const result: ExceptionRecord[] = []
  for (const item of response.exceptions) {
    if (!item || typeof item !== 'object') continue
    const record = item as Record<string, unknown>
    result.push({
      id: textValue(record.id),
      row: numberValue(record.row),
      systemTime: textValue(record.systemTime),
      documentNo: textValue(record.documentNo),
      sku: textValue(record.sku),
      productName: textValue(record.productName),
      spec: textValue(record.spec),
      quantity: numberValue(record.quantity),
      unitCost: numberValue(record.unitCost),
      amount: numberValue(record.amount),
      type: textValue(record.type),
      reason: textValue(record.reason),
    })
  }
  return result
}

function buildDownloads(response: UploadReconciliationResponse): DownloadFile[] {
  if (!Array.isArray(response.downloads)) {
    return initialTask.downloads.map((file) => ({ ...file }))
  }

  return response.downloads.map((file) => ({
    id: file.id,
    name: file.name,
    type: file.type,
    enabled: file.enabled,
    url: file.url,
  }))
}

function textValue(value: unknown) {
  if (value === null || value === undefined) return ''
  return String(value)
}

function numberValue(value: unknown) {
  if (typeof value === 'number') return value
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value)
    if (!Number.isNaN(parsed)) return parsed
  }
  return 0
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
    const response = await uploadReconciliationFiles(aFileObject.value, bFileObject.value, month.value)

    task.id = response.task_id
    task.status = response.status
    task.title = `${response.task_id} · ${response.status === 'SUCCESS' ? '正式对账验收通过' : '正式对账验收未通过'}`
    task.month = response.month || month.value
    task.progressSteps = getProgressSteps(response.status)
    task.progressDetail = {
      currentText: response.status === 'SUCCESS' ? '核查通过，生成文件可下载' : '核查未通过，请查看验收指标和异常明细',
      progress: 100,
      processedCRecords: response.match_summary?.total_a_records ?? 0,
      totalCRecords: response.match_summary?.total_a_records ?? 0,
      matchedBRecords: response.match_summary?.matched_b_records ?? 0,
      manualReviewCount: response.match_summary?.need_review_count ?? 0,
    }
    task.verifyMetrics = buildVerifyMetrics(response)
    task.coverage = {
      monthlyRecords: response.reverse_verify_summary?.monthly_records ?? 0,
      acceptedByC: response.reverse_verify_summary?.accepted_by_c ?? 0,
      markedMissing: response.reverse_verify_summary?.marked_missing ?? 0,
      manuallyExcluded: response.reverse_verify_summary?.manually_excluded ?? 0,
      unexplained: response.reverse_verify_summary?.unexplained ?? 0,
    }
    task.exceptions = buildExceptions(response)
    task.downloads = buildDownloads(response)
    task.createdAt = response.created_at ?? task.createdAt
    task.completedAt = response.completed_at
    aPreview.value = response.a_preview
    llmAnalysis.value = response.llm_result as ExcelLlmAnalysisResult
    productMapping.value = response.product_mapping
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
        <div class="upload-status success">A/B 表完整结构识别完成</div>
        <p class="muted small">A Sheet：{{ aPreview.sheet_name }} ｜ 最大行数：{{ aPreview.max_row }} ｜ 最大列数：{{ aPreview.max_column }}</p>
        <p class="muted small">字段识别、C 表制表、匹配和强制验收结果已写入任务 JSON。</p>

        <details class="mapping-json-block">
          <summary>完整字段识别 JSON</summary>
          <pre>{{ formatJson(llmAnalysis) }}</pre>
        </details>
      </section>

      <section v-if="productMapping" class="panel-card upload-result-card">
        <div class="upload-status success">商品规格映射完成</div>
        <p class="muted small">A列字段：{{ productMapping.a_column_name }} ｜ B列字段：{{ productMapping.b_column_name }}</p>
        <p class="muted small">A字段识别：第 {{ productMapping.structure.a_sheet.header_row_guess }} 行表头 ｜ 置信度 {{ productMapping.structure.a_sheet.confidence }}</p>
        <p class="muted small">B字段识别：第 {{ productMapping.structure.b_sheet.header_row_guess }} 行表头 ｜ 置信度 {{ productMapping.structure.b_sheet.confidence }}</p>
        <p class="muted small">A去重数量：{{ productMapping.summary.a_unique_count }} ｜ B去重数量：{{ productMapping.summary.b_unique_count }}</p>
        <p class="muted small">成功映射：{{ productMapping.summary.mapping_count }} ｜ 待复核：{{ productMapping.summary.need_review_count }}</p>
        <p class="muted small">A未匹配：{{ productMapping.summary.unmatched_a_count }} ｜ B未匹配：{{ productMapping.summary.unmatched_b_count }}</p>

        <details class="mapping-json-block">
          <summary>A 表去重后的商品列表 JSON</summary>
          <pre>{{ formatJson(productMapping.a_unique) }}</pre>
        </details>

        <details class="mapping-json-block">
          <summary>B 表去重后的商品列表 JSON</summary>
          <pre>{{ formatJson(productMapping.b_unique) }}</pre>
        </details>

        <details class="mapping-json-block">
          <summary>完整商品映射结果 JSON</summary>
          <pre>{{ formatJson(productMapping) }}</pre>
        </details>
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
