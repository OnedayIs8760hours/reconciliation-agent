<script setup lang="ts">
import type { Component } from 'vue'
import type { StatusTone } from '@/types/workbench'

withDefaults(
  defineProps<{
    label: string
    tone?: StatusTone
    icon?: Component
  }>(),
  {
    tone: 'neutral',
    icon: undefined,
  },
)
</script>

<template>
  <span class="status-pill" :class="`status-pill--${tone}`">
    <component :is="icon" v-if="icon" class="status-pill__icon" :size="14" aria-hidden="true" />
    <span v-else class="status-pill__dot" aria-hidden="true" />
    <span>{{ label }}</span>
  </span>
</template>
