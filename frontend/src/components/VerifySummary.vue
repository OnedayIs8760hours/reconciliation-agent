<script setup lang="ts">
import { CheckCircle2, AlertTriangle } from '@lucide/vue'
import type { TaskStatus, VerifyMetric } from '@/types/reconciliation'

defineProps<{
  metrics: VerifyMetric[]
  status: TaskStatus
}>()
</script>

<template>
  <section class="verify-summary result-card">
    <div class="card-heading compact">
      <div>
        <span class="section-kicker">核查结果</span>
        <h2>核心指标</h2>
      </div>
      <button v-if="status === 'FAILED'" class="ghost-button" type="button">查看异常明细</button>
    </div>

    <div class="metric-grid">
      <article v-for="metric in metrics" :key="metric.label" :class="['metric-tile', metric.passed ? 'passed' : 'attention']">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
        <small>
          <CheckCircle2 v-if="metric.passed" :size="16" />
          <AlertTriangle v-else :size="16" />
          {{ metric.hint }}
        </small>
      </article>
    </div>

    <div v-if="status === 'SUCCESS'" class="final-state success-state">
      <CheckCircle2 :size="28" />
      <div>
        <strong>核查通过</strong>
        <p>A/C 数量口径一致，A/C 金额口径一致，B 表本月记录已全部承接或说明，Excel 公式检查通过。</p>
      </div>
    </div>

    <div v-else-if="status === 'FAILED'" class="final-state failed-state">
      <AlertTriangle :size="28" />
      <div>
        <strong>对账核查未通过</strong>
        <p>存在未解释记录或差额，任务不能标记为绿色完成，请进入异常明细复核。</p>
      </div>
    </div>
  </section>
</template>
