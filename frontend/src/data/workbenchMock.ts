import type { AlignmentStep, DifferenceSummary, WorkbenchMetric, WorkQueueRecord } from '@/types/workbench'

export const alignmentSteps: AlignmentStep[] = [
  { id: 'import', label: '导入', state: 'done' },
  { id: 'match', label: '匹配', state: 'done' },
  { id: 'review', label: '复核', state: 'active' },
  { id: 'settle', label: '结清', state: 'pending' },
]

export const workbenchMetrics: WorkbenchMetric[] = [
  {
    id: 'matched-amount',
    label: '已匹配金额',
    value: '¥ 2,418,930',
    detail: '覆盖本月 94.2% 入出库流水',
    tone: 'success',
  },
  {
    id: 'open-differences',
    label: '待处理差异',
    value: '3 项',
    detail: '优先处理金额不一致批次',
    tone: 'warning',
  },
  {
    id: 'blocked-batches',
    label: '异常批次',
    value: '1 个',
    detail: '缺少银行流水，需要补充文件',
    tone: 'danger',
  },
]

export const workQueue: WorkQueueRecord[] = [
  {
    id: 'TZ-202607-014',
    batchName: '台州七月原料入库',
    source: 'A 表 / 台州 B 表',
    differenceType: '金额不一致',
    amount: '¥ 18,420.00',
    owner: '财务复核',
    statusLabel: '待人工确认',
    statusTone: 'warning',
    actionLabel: '进入复核',
  },
  {
    id: 'HZ-202607-032',
    batchName: '杭州客户回款核对',
    source: '银行流水 / 应收台账',
    differenceType: '缺失流水',
    amount: '¥ 6,800.00',
    owner: '资料补充',
    statusLabel: '需补充文件',
    statusTone: 'danger',
    actionLabel: '查看缺口',
  },
  {
    id: 'NB-202607-008',
    batchName: '宁波供应商付款',
    source: '付款清单 / 系统出库',
    differenceType: '重复记录',
    amount: '¥ 2,160.00',
    owner: '系统建议',
    statusLabel: '建议合并',
    statusTone: 'info',
    actionLabel: '检查建议',
  },
]

export const differenceSummary: DifferenceSummary[] = [
  {
    id: 'amount',
    label: '金额不一致',
    count: 1,
    description: '金额、方向或税额口径需要复核。',
    tone: 'warning',
  },
  {
    id: 'missing',
    label: '缺失流水',
    count: 1,
    description: 'B 表本月记录未被 C 表承接。',
    tone: 'danger',
  },
  {
    id: 'duplicate',
    label: '重复记录',
    count: 1,
    description: '疑似多行承接同一业务记录。',
    tone: 'info',
  },
]
