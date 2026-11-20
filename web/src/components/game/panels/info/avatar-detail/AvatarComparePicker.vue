<script setup lang="ts">
import type { SimpleAvatarDTO } from '@/types/api'
import searchIcon from '@/assets/icons/ui/lucide/search.svg'

defineProps<{
  title: string
  candidates: SimpleAvatarDTO[]
  search: string
  placeholder: string
  emptyText: string
  errorText: string
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'update:search', value: string): void
  (e: 'select', id: string): void
}>()

function handleInput(event: Event) {
  emit('update:search', (event.target as HTMLInputElement).value)
}
</script>

<template>
  <div class="compare-picker">
    <div class="picker-title">{{ title }}</div>
    <label class="search-box">
      <span class="search-icon" :style="{ '--icon-url': `url(${searchIcon})` }" aria-hidden="true"></span>
      <input
        class="search-input"
        type="text"
        :value="search"
        :placeholder="placeholder"
        @input="handleInput"
      />
    </label>
    <div v-if="errorText" class="picker-error">{{ errorText }}</div>
    <ul v-else-if="candidates.length" class="candidate-list">
      <li v-for="avatar in candidates" :key="avatar.id">
        <button
          type="button"
          class="candidate"
          :data-avatar-id="avatar.id"
          @click="emit('select', avatar.id)"
        >
          <span class="candidate-name">{{ avatar.name }}</span>
          <span class="candidate-meta">{{ avatar.cultivation_display || avatar.realm }} · {{ avatar.sect_name }}</span>
        </button>
      </li>
    </ul>
    <div v-else-if="!loading" class="picker-empty">{{ emptyText }}</div>
  </div>
</template>

<style scoped>
.compare-picker {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 200px;
}

.picker-title {
  font-size: 13px;
  color: #c8c4ba;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border: 1px solid #3a362f;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.04);
}

.search-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  color: #90897c;
  background-color: currentColor;
  -webkit-mask: var(--icon-url) center / contain no-repeat;
  mask: var(--icon-url) center / contain no-repeat;
}

.search-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: #f3f1ec;
  font-size: 13px;
}

.candidate-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 50vh;
  overflow-y: auto;
}

.candidate {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  padding: 7px 10px;
  border: 1px solid transparent;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.03);
  color: #f3f1ec;
  cursor: pointer;
  text-align: left;
  font-size: 13px;
}

.candidate:hover {
  border-color: rgba(120, 182, 255, 0.45);
  background: rgba(120, 182, 255, 0.08);
}

.candidate-meta {
  color: #90897c;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.picker-empty,
.picker-error {
  font-size: 12px;
  color: #90897c;
  padding: 8px 0;
}

.picker-error {
  color: #d48370;
}
</style>
