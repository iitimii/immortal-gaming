<script setup lang="ts">
import { toRef } from 'vue'
import { NButton, NPopover, NRadio, NRadioButton, NRadioGroup } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import downloadIcon from '@/assets/icons/ui/lucide/download.svg'
import { useEventExport } from '@/composables/useEventExport'

const props = defineProps<{
  /** Avatar the event panel is filtered to; empty when unfiltered. */
  avatarId: string
}>()

const { t } = useI18n()
const {
  showMenu,
  exportFormat,
  exportScope,
  exporting,
  formatOptions,
  scopeOptions,
  runExport,
} = useEventExport(toRef(props, 'avatarId'))
</script>

<template>
  <n-popover v-model:show="showMenu" trigger="click" placement="bottom-end" :show-arrow="false">
    <template #trigger>
      <button
        type="button"
        class="event-export-trigger"
        :title="t('game.event_panel.export_title')"
        data-testid="event-export-trigger"
      >
        <span class="event-export-icon" :style="{ '--icon-url': `url(${downloadIcon})` }" aria-hidden="true"></span>
        <span>{{ t('game.event_panel.export') }}</span>
      </button>
    </template>
    <div class="event-export-menu" data-testid="event-export-menu">
      <div class="event-export-title">{{ t('game.event_panel.export_title') }}</div>
      <div class="event-export-label">{{ t('game.event_panel.export_format') }}</div>
      <n-radio-group v-model:value="exportFormat" size="small" data-testid="event-export-format">
        <n-radio-button
          v-for="option in formatOptions"
          :key="option.value"
          :value="option.value"
          :label="option.label"
        />
      </n-radio-group>
      <div class="event-export-label">{{ t('game.event_panel.export_scope') }}</div>
      <n-radio-group v-model:value="exportScope" data-testid="event-export-scope">
        <div class="event-export-scopes">
          <n-radio
            v-for="option in scopeOptions"
            :key="option.value"
            :value="option.value"
            :label="option.label"
          />
        </div>
      </n-radio-group>
      <n-button
        type="primary"
        size="small"
        block
        :loading="exporting"
        :disabled="exporting"
        class="event-export-submit"
        data-testid="event-export-submit"
        @click="runExport"
      >
        {{ t('game.event_panel.export_download') }}
      </n-button>
    </div>
  </n-popover>
</template>

<style scoped>
.event-export-trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 22px;
  padding: 0 8px;
  border: 1px solid #3a3a3a;
  border-radius: 3px;
  background: #2a2a2a;
  color: #ccc;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.event-export-trigger:hover {
  color: #fff;
  border-color: #555;
}

.event-export-icon {
  width: 13px;
  height: 13px;
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

.event-export-menu {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 220px;
}

.event-export-title {
  font-size: 13px;
  font-weight: 600;
}

.event-export-label {
  margin-top: 4px;
  font-size: 11px;
  color: #999;
}

.event-export-scopes {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.event-export-submit {
  margin-top: 6px;
}
</style>
