<script setup lang="ts">
import { computed, ref } from 'vue'
import TaskProgress from '@/components/TaskProgress.vue'
import VerifySummary from '@/components/VerifySummary.vue'
import CoverageStatistics from '@/components/CoverageStatistics.vue'
import ResultDownload from '@/components/ResultDownload.vue'
import ExceptionDrawer from '@/components/ExceptionDrawer.vue'
import { taskHistory } from '@/api/reconciliation'

const selectedId = ref(taskHistory[0]?.id ?? '')
const drawerOpen = ref(false)

const selectedTask = computed(() => taskHistory.find((task) => task.id === selectedId.value) ?? taskHistory[0])
</script>

<template>
  <div class="history-page">
    <section class="history-list result-card">
      <div class="card-heading compact">
        <div>
          <span class="section-kicker">任务记录</span>
          <h1>对账任务</h1>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>任务编号</th>
              <th>A表文件名</th>
              <th>B表文件名</th>
              <th>月份</th>
              <th>状态</th>
              <th>A/C金额差额</th>
              <th>B表未解释</th>
              <th>创建时间</th>
              <th>完成时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in taskHistory" :key="task.id" :class="{ selected: task.id === selectedId }" @click="selectedId = task.id">
              <td>{{ task.id }}</td>
              <td>{{ task.aFile.name }}</td>
              <td>{{ task.bFile.name }}</td>
              <td>{{ task.month }}</td>
              <td>{{ task.status === 'SUCCESS' ? '✓ 已通过' : '⚠ 未通过' }}</td>
              <td>{{ task.verifyMetrics[1]?.value }}</td>
              <td>{{ task.coverage.unexplained }}</td>
              <td>{{ task.createdAt }}</td>
              <td>{{ task.completedAt ?? '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="selectedTask" class="task-detail">
      <div class="result-card task-info">
        <span class="section-kicker">任务详情</span>
        <h2>{{ selectedTask.title }}</h2>
        <p>A表：{{ selectedTask.aFile.name }}</p>
        <p>B表：{{ selectedTask.bFile.name }}</p>
        <p>月份：{{ selectedTask.month }}</p>
      </div>
      <TaskProgress :title="selectedTask.title" :steps="selectedTask.progressSteps" :detail="selectedTask.progressDetail" />
      <VerifySummary :metrics="selectedTask.verifyMetrics" :status="selectedTask.status" />
      <CoverageStatistics :coverage="selectedTask.coverage" />
      <section class="exception-summary result-card">
        <div>
          <span class="section-kicker">异常明细</span>
          <h2>{{ selectedTask.exceptions.length ? `${selectedTask.exceptions.length} 条需要复核` : '暂无异常记录' }}</h2>
        </div>
        <button class="ghost-button" type="button" :disabled="!selectedTask.exceptions.length" @click="drawerOpen = true">查看异常明细</button>
      </section>
      <ResultDownload :files="selectedTask.downloads" :status="selectedTask.status" />
    </section>

    <ExceptionDrawer :open="drawerOpen" :records="selectedTask?.exceptions ?? []" @close="drawerOpen = false" />
  </div>
</template>
