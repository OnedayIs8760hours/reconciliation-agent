// 对账 API 调用。

import type { DownloadFile, ReconciliationTask } from '@/types/reconciliation'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:6161'

export interface UploadReconciliationResponse {
  task_id: string
  status: 'UPLOADED'
}

export interface RunReconciliationRequest {
  month: string
}

export const initialTask: ReconciliationTask = {
  id: 'REC-MOCK',
  title: '等待创建对账任务',
  targetName: '对账任务',
  month: '2026-07',
  status: 'UPLOADED',
  aFile: {
    name: '',
    size: '',
    uploaded: false,
  },
  bFile: {
    name: '',
    size: '',
    uploaded: false,
    recognized: false,
  },
  progressSteps: [
    { id: 1, title: '文件检查', status: 'pending' },
    { id: 2, title: '生成 C 表底稿', status: 'pending' },
    { id: 3, title: 'A/B 数据匹配', status: 'pending' },
    { id: 4, title: 'B 表反向核查', status: 'pending' },
    { id: 5, title: '最终验收', status: 'pending' },
  ],
  progressDetail: {
    currentText: '上传 A 表、B 表并选择对账月份后开始',
    progress: 0,
    processedCRecords: 0,
    totalCRecords: 0,
    matchedBRecords: 0,
    manualReviewCount: 0,
  },
  verifyMetrics: [
    { label: 'A/C 数量差额', value: '-', passed: false, hint: '等待生成 C 表' },
    { label: 'A/C 金额差额', value: '-', passed: false, hint: '等待金额核验' },
    { label: 'B表未解释记录', value: '-', passed: false, hint: '等待反向核查' },
    { label: 'Excel公式错误', value: '-', passed: false, hint: '等待公式检查' },
  ],
  coverage: {
    monthlyRecords: 0,
    acceptedByC: 0,
    markedMissing: 0,
    manuallyExcluded: 0,
    unexplained: 0,
  },
  exceptions: [],
  downloads: [
    { id: 'c-table', name: 'C.xlsx', type: 'excel', enabled: false },
    { id: 'verify-report', name: '核查报告.json', type: 'report', enabled: false },
  ],
  createdAt: '',
}

export const taskHistory: ReconciliationTask[] = []

export async function uploadReconciliationFiles(aFile: File, bFile: File): Promise<UploadReconciliationResponse> {
  const formData = new FormData()
  formData.append('a_file', aFile)
  formData.append('b_file', bFile)

  const response = await fetch(`${API_BASE_URL}/api/reconciliation/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, '上传失败'))
  }

  const data = (await response.json()) as UploadReconciliationResponse
  if (!data?.task_id) {
    throw new Error('上传成功但未返回 task_id')
  }

  return data
}

export async function runReconciliation(taskId: string, month: string): Promise<ReconciliationTask> {
  const response = await fetch(`${API_BASE_URL}/api/reconciliation/${taskId}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ month }),
  })

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, '启动对账失败'))
  }

  return (await response.json()) as ReconciliationTask
}

export async function getReconciliationTask(taskId: string): Promise<ReconciliationTask> {
  const response = await fetch(`${API_BASE_URL}/api/reconciliation/${taskId}`)
  if (!response.ok) {
    throw new Error(await readErrorMessage(response, '查询任务失败'))
  }
  return (await response.json()) as ReconciliationTask
}

export function getTaskDownloadUrl(taskId: string, kind: DownloadFile['id'] | 'c' | 'report'): string {
  const downloadKind = kind === 'verify-report' || kind === 'report' ? 'report' : 'c'
  return `${API_BASE_URL}/api/reconciliation/${taskId}/download/${downloadKind}`
}

async function readErrorMessage(response: Response, fallback: string): Promise<string> {
  let message = `${fallback}（${response.status}）`
  try {
    const payload = await response.json()
    if (typeof payload?.detail === 'string') {
      message = payload.detail
    } else if (Array.isArray(payload?.detail)) {
      message = payload.detail
        .map((item: { msg?: string }) => item?.msg)
        .filter(Boolean)
        .join('；')
    }
  } catch {
    const text = await response.text()
    if (text) {
      message = text
    }
  }
  return message
}
