export type TaskStatus =
  | 'UPLOADED'
  | 'PROCESSING'
  | 'GENERATING'
  | 'MATCHING'
  | 'VERIFYING'
  | 'SUCCESS'
  | 'FAILED'

export type ProgressStepStatus = 'done' | 'active' | 'pending' | 'failed'

export interface UploadedFileInfo {
  name: string
  size: string
  uploaded: boolean
  recognized?: boolean
  warning?: string
}

export interface ProgressStep {
  id: number
  title: string
  status: ProgressStepStatus
}

export interface TaskProgressDetail {
  currentText: string
  progress: number
  processedCRecords: number
  totalCRecords: number
  matchedBRecords: number
  manualReviewCount: number
}

export interface VerifyMetric {
  label: string
  value: string | number
  passed: boolean
  hint: string
}

export interface CoverageStatistics {
  monthlyRecords: number
  acceptedByC: number
  markedMissing: number
  manuallyExcluded: number
  unexplained: number
}

export interface ExceptionRecord {
  id: string
  row: number
  systemTime: string
  documentNo: string
  sku: string
  productName: string
  spec: string
  quantity: number
  unitCost: number
  amount: number
  type: string
  reason: string
}

export interface DownloadFile {
  id: string
  name: string
  type: 'excel' | 'report'
  enabled: boolean
}

export interface ReconciliationTask {
  id: string
  title: string
  targetName: string
  month: string
  status: TaskStatus
  aFile: UploadedFileInfo
  bFile: UploadedFileInfo
  progressSteps: ProgressStep[]
  progressDetail: TaskProgressDetail
  verifyMetrics: VerifyMetric[]
  coverage: CoverageStatistics
  exceptions: ExceptionRecord[]
  downloads: DownloadFile[]
  createdAt: string
  completedAt?: string
}
