<script setup lang="ts">
import { Check, Circle, LoaderCircle, X } from '@lucide/vue'
import type { ProgressStep, TaskProgressDetail } from '@/types/reconciliation'

defineProps<{
  title: string
  steps: ProgressStep[]
  detail: TaskProgressDetail
}>()
</script>

<template>
  <section class="task-progress result-card">
    <div class="card-heading">
      <div>
        <span class="section-kicker">对账任务</span>
        <h2>{{ title }}</h2>
      </div>
      <span class="progress-badge">{{ detail.progress }}%</span>
    </div>

    <ol class="step-list">
      <li v-for="step in steps" :key="step.id" :class="['step-item', step.status]">
        <span class="step-icon">
          <Check v-if="step.status === 'done'" :size="15" />
          <LoaderCircle v-else-if="step.status === 'active'" :size="15" class="spin" />
          <X v-else-if="step.status === 'failed'" :size="15" />
          <Circle v-else :size="15" />
        </span>
        {{ step.id }}. {{ step.title }}
      </li>
    </ol>

    <div class="current-node">
      <strong>当前：{{ detail.currentText }}</strong>
      <div class="progress-track"><span :style="{ width: `${detail.progress}%` }"></span></div>
      <div class="progress-facts">
        <span>已处理 C 表业务记录：{{ detail.processedCRecords }} / {{ detail.totalCRecords }}</span>
        <span>已匹配 B 表记录：{{ detail.matchedBRecords }}</span>
        <span>需要人工复核：{{ detail.manualReviewCount }}</span>
      </div>
    </div>
  </section>
</template>
