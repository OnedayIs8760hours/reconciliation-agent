<script setup lang="ts">
import { ArrowRight } from '@lucide/vue'

import type { WorkQueueRecord } from '@/types/workbench'
import StatusPill from './StatusPill.vue'

defineProps<{
  record: WorkQueueRecord
}>()
</script>

<template>
  <article class="queue-item">
    <div class="queue-item__main">
      <p class="queue-item__id">{{ record.id }}</p>
      <h3 class="queue-item__title">{{ record.batchName }}</h3>
      <p class="queue-item__source">{{ record.source }}</p>
    </div>

    <dl class="queue-item__facts" aria-label="待处理批次信息">
      <div>
        <dt>差异类型</dt>
        <dd>{{ record.differenceType }}</dd>
      </div>
      <div>
        <dt>差异金额</dt>
        <dd>{{ record.amount }}</dd>
      </div>
      <div>
        <dt>处理方</dt>
        <dd>{{ record.owner }}</dd>
      </div>
    </dl>

    <div class="queue-item__action">
      <StatusPill :tone="record.statusTone" :label="record.statusLabel" />
      <button class="queue-item__button" type="button">
        <span>{{ record.actionLabel }}</span>
        <ArrowRight :size="16" aria-hidden="true" />
      </button>
    </div>
  </article>
</template>
