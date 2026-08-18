<script setup lang="ts">
defineProps<{
  eyebrow?: string
  title: string
  description?: string
}>()
</script>

<template>
  <div class="section-header">
    <p v-if="eyebrow" class="section-header__eyebrow">{{ eyebrow }}</p>
    <h2 class="section-header__title">{{ title }}</h2>
    <p v-if="description" class="section-header__description">{{ description }}</p>
  </div>
</template>
