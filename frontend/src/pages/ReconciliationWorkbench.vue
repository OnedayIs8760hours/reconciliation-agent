<script setup lang="ts">
import { AlertTriangle, ArrowRight, FileCheck2, ListChecks, UploadCloud } from '@lucide/vue'

import ActionButton from '@/components/ActionButton.vue'
import MetricTile from '@/components/MetricTile.vue'
import SectionHeader from '@/components/SectionHeader.vue'
import StatusPill from '@/components/StatusPill.vue'
import WorkQueueItem from '@/components/WorkQueueItem.vue'
import { alignmentSteps, differenceSummary, workbenchMetrics, workQueue } from '@/data/workbenchMock'

const statusPills = [
  { id: 'synced', label: '数据已同步', tone: 'success' as const },
  { id: 'review', label: '2 个批次待复核', tone: 'warning' as const },
  { id: 'blocked', label: '1 个异常需确认', tone: 'danger' as const },
]
</script>

<template>
  <section class="workbench" aria-labelledby="workbench-title">
    <div class="workbench__hero">
      <div class="workbench__copy">
        <p class="workbench__eyebrow">对账工作台</p>
        <h2 id="workbench-title" class="workbench__title">今天先处理 3 个未结清差异</h2>
        <p class="workbench__lead">
          导入账单、核对流水、复核差异并导出结果。工作台会优先显示需要人工确认的批次。
        </p>

        <div class="workbench__actions" aria-label="主要操作">
          <ActionButton>
            <UploadCloud :size="18" aria-hidden="true" />
            <span>上传对账文件</span>
          </ActionButton>
          <ActionButton variant="secondary">
            <ListChecks :size="18" aria-hidden="true" />
            <span>查看差异队列</span>
          </ActionButton>
        </div>

        <div class="workbench__status" aria-label="当前状态摘要">
          <StatusPill
            v-for="pill in statusPills"
            :key="pill.id"
            :label="pill.label"
            :tone="pill.tone"
          />
        </div>
      </div>

      <aside class="workbench__panel material-panel" aria-labelledby="summary-title">
        <SectionHeader
          eyebrow="今日进度"
          title="对齐轨道"
          description="导入、匹配、复核、结清四步保持可追溯。"
        />

        <ol class="alignment-track" aria-label="对账流程状态">
          <li
            v-for="step in alignmentSteps"
            :key="step.id"
            class="alignment-track__step"
            :class="`alignment-track__step--${step.state}`"
          >
            <span class="alignment-track__node" aria-hidden="true" />
            <span class="alignment-track__label">{{ step.label }}</span>
            <span class="alignment-track__state">
              {{ step.state === 'done' ? '已完成' : step.state === 'active' ? '处理中' : '待开始' }}
            </span>
          </li>
        </ol>

        <div class="workbench__metrics" id="summary-title">
          <MetricTile v-for="metric in workbenchMetrics" :key="metric.id" :metric="metric" />
        </div>
      </aside>
    </div>

    <div class="workbench__grid">
      <section class="workbench__queue-panel material-panel" aria-labelledby="queue-title">
        <SectionHeader
          title="待处理队列"
          description="按交付风险排序，优先处理影响 C 表验收的批次。"
        />
        <div id="queue-title" class="visually-hidden">待处理队列</div>
        <div class="workbench__queue-list">
          <WorkQueueItem v-for="record in workQueue" :key="record.id" :record="record" />
        </div>
      </section>

      <aside class="workbench__side-panel" aria-label="差异概览和下一步建议">
        <section class="material-panel workbench__difference-panel">
          <SectionHeader title="差异概览" description="每一项都需要文字结论，不能只依赖颜色判断。" />
          <div class="difference-list">
            <article
              v-for="item in differenceSummary"
              :key="item.id"
              class="difference-card"
              :class="`difference-card--${item.tone}`"
            >
              <span class="difference-card__count">{{ item.count }}</span>
              <div>
                <h3>{{ item.label }}</h3>
                <p>{{ item.description }}</p>
              </div>
            </article>
          </div>
        </section>

        <section class="material-panel next-step-panel">
          <div class="next-step-panel__icon" aria-hidden="true">
            <FileCheck2 :size="22" />
          </div>
          <SectionHeader title="下一步建议" description="先处理金额不一致，再导出复核清单。" />
          <p class="next-step-panel__note">
            有 1 个批次缺少银行流水，请补充文件后重新匹配，避免交付前核查失败。
          </p>
          <button class="next-step-panel__button" type="button">
            <AlertTriangle :size="16" aria-hidden="true" />
            <span>查看异常批次</span>
            <ArrowRight :size="16" aria-hidden="true" />
          </button>
        </section>
      </aside>
    </div>
  </section>
</template>
