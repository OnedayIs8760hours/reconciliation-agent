<script setup lang="ts">
defineProps<{
  month: string
  canStart: boolean
  running: boolean
}>()

const emit = defineEmits<{
  'update:month': [value: string]
  start: []
}>()
</script>

<template>
  <section class="settings-card panel-card">
    <div class="section-kicker">② 对账设置</div>
    <label class="field-label" for="reconcile-month">对账月份</label>
    <input
      id="reconcile-month"
      class="month-input"
      type="month"
      :value="month"
      @input="emit('update:month', ($event.target as HTMLInputElement).value)"
    />
    <p class="muted small">反向核查仅覆盖该月份的系统出入库记录。</p>

    <button class="primary-action" type="button" :disabled="!canStart || running" @click="emit('start')">
      {{ running ? '正在对账...' : '开始智能对账' }}
    </button>
  </section>
</template>
