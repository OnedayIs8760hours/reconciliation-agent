<script setup lang="ts">
import { computed, ref } from 'vue'
import { X } from '@lucide/vue'
import type { ExceptionRecord } from '@/types/reconciliation'

const props = defineProps<{
  open: boolean
  records: ExceptionRecord[]
}>()

const emit = defineEmits<{
  close: []
}>()

const selectedId = ref<string | null>(null)

const selectedRecord = computed(() => {
  return props.records.find((record) => record.id === selectedId.value) ?? props.records[0]
})
</script>

<template>
  <div v-if="open" class="drawer-mask" @click.self="emit('close')">
    <aside class="exception-drawer" aria-label="异常记录">
      <header>
        <div>
          <span class="section-kicker">异常记录</span>
          <h2>B 表反向核查明细</h2>
        </div>
        <button class="icon-button" type="button" @click="emit('close')"><X :size="20" /></button>
      </header>

      <div v-if="records.length" class="drawer-content">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>行号</th>
                <th>系统时间</th>
                <th>单据编号</th>
                <th>规格</th>
                <th>数量</th>
                <th>异常类型</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="record in records"
                :key="record.id"
                :class="{ selected: selectedRecord?.id === record.id }"
                @click="selectedId = record.id"
              >
                <td>{{ record.row }}</td>
                <td>{{ record.systemTime.slice(5, 10) }}</td>
                <td>{{ record.documentNo }}</td>
                <td>{{ record.spec }}</td>
                <td>{{ record.quantity }}</td>
                <td>{{ record.type }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <section v-if="selectedRecord" class="trace-card">
          <h3>完整追溯信息</h3>
          <dl>
            <div><dt>B表行号</dt><dd>{{ selectedRecord.row }}</dd></div>
            <div><dt>系统出入库时间</dt><dd>{{ selectedRecord.systemTime }}</dd></div>
            <div><dt>单据编号</dt><dd>{{ selectedRecord.documentNo }}</dd></div>
            <div><dt>货品编号</dt><dd>{{ selectedRecord.sku }}</dd></div>
            <div><dt>货品名称</dt><dd>{{ selectedRecord.productName }}</dd></div>
            <div><dt>规格</dt><dd>{{ selectedRecord.spec }}</dd></div>
            <div><dt>入库数量</dt><dd>{{ selectedRecord.quantity }}</dd></div>
            <div><dt>入库成本单价</dt><dd>{{ selectedRecord.unitCost.toFixed(2) }}</dd></div>
            <div><dt>入库成本金额</dt><dd>{{ selectedRecord.amount.toFixed(2) }}</dd></div>
            <div class="full"><dt>异常原因</dt><dd>{{ selectedRecord.reason }}</dd></div>
          </dl>
        </section>
      </div>

      <p v-else class="empty-state">当前没有异常记录。</p>
    </aside>
  </div>
</template>
