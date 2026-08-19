<script setup lang="ts">
defineProps<{
  activeView: 'workbench' | 'history'
}>()

const emit = defineEmits<{
  navigate: [view: 'workbench' | 'history']
}>()
</script>

<template>
  <header class="app-header">
    <button class="brand" type="button" @click="emit('navigate', 'workbench')">
      <span class="brand-mark">财</span>
      <span>财务智能对账</span>
    </button>
    <nav>
      <button :class="{ active: activeView === 'workbench' }" type="button" @click="emit('navigate', 'workbench')">对账工作台</button>
      <button :class="{ active: activeView === 'history' }" type="button" @click="emit('navigate', 'history')">任务记录</button>
    </nav>
  </header>
</template>
