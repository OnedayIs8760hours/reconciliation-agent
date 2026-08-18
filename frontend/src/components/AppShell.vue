<script setup lang="ts">
import { CircleHelp, Circle } from '@lucide/vue'
</script>

<template>
  <div class="app-shell">
    <header class="topbar" aria-label="应用顶部栏">
      <div class="topbar__brand" aria-label="当前产品">
        <div class="topbar__mark" aria-hidden="true">
          <Circle :size="10" stroke-width="3" />
        </div>
        <div>
          <p class="topbar__eyebrow">Reconciliation Agent</p>
          <h1 class="topbar__title">对账工作台</h1>
        </div>
      </div>

      <nav class="topbar__meta" aria-label="工作台状态">
        <span class="topbar__date">2026 年 8 月 18 日</span>
        <span class="topbar__state">本地原型</span>
        <button class="topbar__help" type="button" aria-label="查看帮助">
          <CircleHelp :size="18" aria-hidden="true" />
        </button>
      </nav>
    </header>

    <main class="app-shell__main">
      <slot />
    </main>
  </div>
</template>
