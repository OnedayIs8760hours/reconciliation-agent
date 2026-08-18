export type StatusTone = 'neutral' | 'success' | 'warning' | 'danger' | 'info'

export interface WorkbenchMetric {
  id: string
  label: string
  value: string
  detail: string
  tone: StatusTone
}

export interface WorkQueueRecord {
  id: string
  batchName: string
  source: string
  differenceType: string
  amount: string
  owner: string
  statusLabel: string
  statusTone: StatusTone
  actionLabel: string
}

export interface DifferenceSummary {
  id: string
  label: string
  count: number
  description: string
  tone: StatusTone
}

export interface AlignmentStep {
  id: string
  label: string
  state: 'done' | 'active' | 'pending'
}
