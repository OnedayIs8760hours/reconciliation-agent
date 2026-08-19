<script setup lang="ts">
import { ref } from 'vue'
import AppHeader from '@/components/AppHeader.vue'
import Reconciliation from '@/views/Reconciliation.vue'
import TaskHistory from '@/views/TaskHistory.vue'

const activeView = ref<'workbench' | 'history'>('workbench')
</script>

<template>
  <div class="app-shell">
    <AppHeader :active-view="activeView" @navigate="activeView = $event" />
    <Reconciliation v-if="activeView === 'workbench'" />
    <TaskHistory v-else />
  </div>
</template>
