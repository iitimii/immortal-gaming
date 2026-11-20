<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import stepForwardIcon from '@/assets/icons/ui/lucide/step-forward.svg'

const props = defineProps<{
  enabled: boolean
  busy: boolean
}>()

const emit = defineEmits<{
  (e: 'step'): void
}>()

const { t } = useI18n()

const isDisabled = computed(() => props.busy || !props.enabled)

const title = computed(() => {
  if (props.busy) return t('game.controls.step_once_busy')
  if (!props.enabled) return t('game.controls.step_once_unavailable')
  return t('game.controls.step_once')
})

function onClick() {
  if (isDisabled.value) return
  emit('step')
}
</script>

<template>
  <button
    type="button"
    class="step-once-btn"
    :class="{ 'step-once-btn--busy': busy }"
    :disabled="isDisabled"
    :aria-busy="busy"
    :aria-label="t('game.controls.step_once')"
    :title="title"
    @click="onClick"
  >
    <span
      class="step-once-icon"
      :style="{ '--icon-url': `url(${stepForwardIcon})` }"
      aria-hidden="true"
    ></span>
  </button>
</template>

<style scoped>
.step-once-btn {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid #444;
  color: #ddd;
  width: 40px;
  height: 40px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    background 0.16s ease,
    border-color 0.16s ease,
    color 0.16s ease,
    opacity 0.16s ease;
}

.step-once-icon {
  width: 18px;
  height: 18px;
  display: inline-block;
  background-color: currentColor;
  -webkit-mask-image: var(--icon-url);
  mask-image: var(--icon-url);
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-position: center;
  -webkit-mask-size: contain;
  mask-size: contain;
}

.step-once-btn:not(:disabled):hover {
  background: rgba(32, 28, 20, 0.82);
  border-color: rgba(232, 202, 143, 0.56);
  color: #fff;
}

.step-once-btn:focus-visible {
  outline: 2px solid rgba(232, 202, 143, 0.74);
  outline-offset: 2px;
}

.step-once-btn:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

.step-once-btn--busy:disabled {
  cursor: progress;
  opacity: 0.75;
}

.step-once-btn--busy .step-once-icon {
  animation: step-once-pulse 0.9s ease-in-out infinite;
}

@keyframes step-once-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}
</style>
