<script setup lang="ts">
import type { WorldStatisticsBucket } from '@/types/core'

defineProps<{
  buckets: WorldStatisticsBucket[]
  emptyText: string
  formatPercent: (value: number) => string
}>()
</script>

<template>
  <ul v-if="buckets.length" class="bar-list">
    <li v-for="bucket in buckets" :key="bucket.id" class="bar-row" :data-bucket-id="bucket.id">
      <span class="bar-label" :title="bucket.label">{{ bucket.label }}</span>
      <span class="bar-track" aria-hidden="true">
        <span class="bar-fill" :style="{ width: `${bucket.percent}%` }"></span>
      </span>
      <span class="bar-value">
        {{ bucket.count }}
        <span class="bar-percent">{{ formatPercent(bucket.percent) }}</span>
      </span>
    </li>
  </ul>
  <div v-else class="bar-empty">{{ emptyText }}</div>
</template>

<style scoped>
.bar-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bar-row {
  display: grid;
  grid-template-columns: minmax(80px, 34%) 1fr auto;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.bar-label {
  color: var(--panel-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-track {
  position: relative;
  height: 8px;
  border-radius: 4px;
  background: var(--panel-accent-soft);
  overflow: hidden;
}

.bar-fill {
  position: absolute;
  inset: 0 auto 0 0;
  border-radius: 4px;
  background: var(--panel-accent);
}

.bar-value {
  min-width: 72px;
  text-align: right;
  color: var(--panel-text-primary);
  font-variant-numeric: tabular-nums;
}

.bar-percent {
  margin-left: 4px;
  color: var(--panel-text-muted);
}

.bar-empty {
  font-size: 12px;
  color: var(--panel-empty);
}
</style>
