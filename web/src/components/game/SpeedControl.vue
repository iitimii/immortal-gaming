<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  speed: number
  options: number[]
}>()

const emit = defineEmits<{
  (e: 'select', speed: number): void
}>()

const { t } = useI18n()

function formatSpeed(value: number) {
  return t('game.controls.speed_option', { speed: String(value) })
}

function select(value: number) {
  if (value === props.speed) return
  emit('select', value)
}
</script>

<template>
  <div
    v-if="options.length > 0"
    class="speed-control"
    role="group"
    :aria-label="t('game.controls.speed_label')"
    :title="t('game.controls.speed_label')"
  >
    <button
      v-for="option in options"
      :key="option"
      type="button"
      class="speed-option"
      :class="{ 'speed-option--active': option === speed }"
      :aria-pressed="option === speed"
      :title="t('game.controls.speed_set', { speed: String(option) })"
      :data-speed="option"
      @click="select(option)"
    >
      {{ formatSpeed(option) }}
    </button>
  </div>
</template>

<style scoped>
.speed-control {
  display: flex;
  align-items: stretch;
  height: 40px;
  padding: 3px;
  gap: 2px;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid #444;
  border-radius: 4px;
  box-sizing: border-box;
}

.speed-option {
  min-width: 34px;
  padding: 0 6px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 3px;
  color: #aaa;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  cursor: pointer;
  transition:
    background 0.16s ease,
    border-color 0.16s ease,
    color 0.16s ease;
}

.speed-option:hover {
  background: rgba(32, 28, 20, 0.82);
  color: #fff;
}

.speed-option:focus-visible {
  outline: 2px solid rgba(232, 202, 143, 0.74);
  outline-offset: 1px;
}

.speed-option--active {
  background: rgba(232, 202, 143, 0.16);
  border-color: rgba(232, 202, 143, 0.56);
  color: #f3dfb4;
  cursor: default;
}
</style>
