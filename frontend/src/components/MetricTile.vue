<script setup lang="ts">
import type { WorkbenchMetric } from '@/types/workbench'

withDefaults(
  defineProps<{
    metric: WorkbenchMetric
    compact?: boolean
  }>(),
  {
    compact: false,
  },
)
</script>

<template>
  <article class="metric-tile" :class="[`metric-tile--${metric.tone}`, { 'metric-tile--compact': compact }]">
    <div class="metric-tile__label-row">
      <span class="metric-tile__marker" aria-hidden="true" />
      <p class="metric-tile__label">{{ metric.label }}</p>
    </div>
    <strong class="metric-tile__value">{{ metric.value }}</strong>
    <p class="metric-tile__detail">{{ metric.detail }}</p>
  </article>
</template>
