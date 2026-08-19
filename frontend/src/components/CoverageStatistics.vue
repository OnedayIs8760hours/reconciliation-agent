<script setup lang="ts">
import type { CoverageStatistics } from '@/types/reconciliation'

defineProps<{
  coverage: CoverageStatistics
}>()
</script>

<template>
  <section class="coverage-card result-card">
    <span class="section-kicker">B 表本月覆盖情况</span>
    <div class="coverage-list">
      <div><span>本月有效记录</span><strong>{{ coverage.monthlyRecords }}</strong></div>
      <div><span>已进入 C 表</span><strong>{{ coverage.acceptedByC }}</strong></div>
      <div><span>C表缺失已标记</span><strong>{{ coverage.markedMissing }}</strong></div>
      <div><span>人工排除</span><strong>{{ coverage.manuallyExcluded }}</strong></div>
      <div class="coverage-total"><span>未解释记录</span><strong>{{ coverage.unexplained }}</strong></div>
    </div>
  </section>
</template>
