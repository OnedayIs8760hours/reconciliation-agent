import type { ReconciliationTask } from '@/types/reconciliation'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export interface UploadReconciliationResponse {
  task_id: string
  status: 'UPLOADED'
}

export const initialTask: ReconciliationTask = {
  id: 'REC-MOCK',
  title: '等待创建对账任务',
  targetName: '玖鸣',
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
    { id: 'c-table', name: '玖鸣_2026-07_C表.xlsx', type: 'excel', enabled: false },
    { id: 'b-marked', name: '台州市玖鸣_缺失标记.xlsx', type: 'excel', enabled: false },
    { id: 'verify-report', name: '核查报告.json', type: 'report', enabled: false },
  ],
  createdAt: '08-19 14:00',
}

export const successfulTask: ReconciliationTask = {
  ...initialTask,
  id: 'REC001',
  title: '玖鸣 · 2026年7月对账',
  status: 'SUCCESS',
  aFile: {
    name: '2026年7月玖鸣对账单.xlsx',
    size: '1.8 MB',
    uploaded: true,
  },
  bFile: {
    name: '台州市川跃家居用品有限公司.xlsx',
    size: '3.2 MB',
    uploaded: true,
    recognized: true,
  },
  progressSteps: [
    { id: 1, title: '文件检查', status: 'done' },
    { id: 2, title: '生成 C 表底稿', status: 'done' },
    { id: 3, title: 'A/B 数据匹配', status: 'done' },
    { id: 4, title: 'B 表反向核查', status: 'done' },
    { id: 5, title: '最终验收', status: 'done' },
  ],
  progressDetail: {
    currentText: '核查通过，生成文件可下载',
    progress: 100,
    processedCRecords: 541,
    totalCRecords: 541,
    matchedBRecords: 790,
    manualReviewCount: 0,
  },
  verifyMetrics: [
    { label: 'A/C 数量差额', value: 0, passed: true, hint: '数量口径一致' },
    { label: 'A/C 金额差额', value: '¥0.00', passed: true, hint: '金额口径一致' },
    { label: 'B表未解释记录', value: 0, passed: true, hint: '全部承接或说明' },
    { label: 'Excel公式错误', value: 0, passed: true, hint: '未发现错误公式' },
  ],
  coverage: {
    monthlyRecords: 831,
    acceptedByC: 790,
    markedMissing: 41,
    manuallyExcluded: 0,
    unexplained: 0,
  },
  downloads: [
    { id: 'c-table', name: '玖鸣_2026-07_C表.xlsx', type: 'excel', enabled: true },
    { id: 'b-marked', name: '台州市玖鸣_缺失标记.xlsx', type: 'excel', enabled: true },
    { id: 'verify-report', name: '核查报告.json', type: 'report', enabled: true },
  ],
  completedAt: '08-19 14:06',
}

export const failedTask: ReconciliationTask = {
  ...successfulTask,
  id: 'REC002',
  title: '芳华 · 2026年7月对账',
  targetName: '芳华',
  status: 'FAILED',
  aFile: { name: '芳华7月对账单.xlsx', size: '1.5 MB', uploaded: true },
  bFile: { name: '芳华系统出入库.xlsx', size: '2.7 MB', uploaded: true, recognized: true },
  progressSteps: [
    { id: 1, title: '文件检查', status: 'done' },
    { id: 2, title: '生成 C 表底稿', status: 'done' },
    { id: 3, title: 'A/B 数据匹配', status: 'done' },
    { id: 4, title: 'B 表反向核查', status: 'done' },
    { id: 5, title: '最终验收', status: 'failed' },
  ],
  verifyMetrics: [
    { label: 'A/C 数量差额', value: 0, passed: true, hint: '数量口径一致' },
    { label: 'A/C 金额差额', value: '¥120.00', passed: false, hint: '存在金额差额' },
    { label: 'B表未解释记录', value: 3, passed: false, hint: '需要查看异常明细' },
    { label: 'Excel公式错误', value: 0, passed: true, hint: '未发现错误公式' },
  ],
  coverage: {
    monthlyRecords: 612,
    acceptedByC: 594,
    markedMissing: 15,
    manuallyExcluded: 0,
    unexplained: 3,
  },
  exceptions: [
    {
      id: 'EX-438',
      row: 438,
      systemTime: '2026-07-18 15:32',
      documentNo: 'RK202607180031',
      sku: 'ABC0121',
      productName: '示例货品',
      spec: '黑色站脚款 XL',
      quantity: 32,
      unitCost: 12.5,
      amount: 400,
      type: 'B表未承接',
      reason: '未在 C 表中找到对应业务记录',
    },
    {
      id: 'EX-512',
      row: 512,
      systemTime: '2026-07-21 09:18',
      documentNo: 'CK202607210008',
      sku: 'ABC0921',
      productName: '示例货品',
      spec: '白色 L',
      quantity: 15,
      unitCost: 18,
      amount: 270,
      type: '出库缺失',
      reason: 'C 表中未标记该出库记录',
    },
  ],
  downloads: [
    { id: 'c-table', name: '芳华_2026-07_C表草稿.xlsx', type: 'excel', enabled: false },
    { id: 'b-marked', name: '芳华_异常标记.xlsx', type: 'excel', enabled: false },
    { id: 'verify-report', name: '核查报告.json', type: 'report', enabled: true },
  ],
}

export const taskHistory: ReconciliationTask[] = [successfulTask, failedTask]

export async function uploadReconciliationFiles(aFile: File, bFile: File): Promise<UploadReconciliationResponse> {
  const formData = new FormData()
  formData.append('a_file', aFile)
  formData.append('b_file', bFile)

  const response = await fetch(`${API_BASE_URL}/api/reconciliation/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    let message = `上传失败（${response.status}）`

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

    throw new Error(message)
  }

  const data = (await response.json()) as UploadReconciliationResponse
  if (!data?.task_id) {
    throw new Error('上传成功但未返回 task_id')
  }

  return data
}
