<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useKeyboardShortcuts, type KeyboardShortcut } from '@/composables/useKeyboardShortcuts'
import keyboardIcon from '@/assets/icons/ui/lucide/keyboard.svg'
import xIcon from '@/assets/icons/ui/lucide/x.svg'

const { t, te } = useI18n()
const { helpGroups, helpVisible, closeHelp } = useKeyboardShortcuts()

function keycaps(shortcut: KeyboardShortcut): string[] {
  return (shortcut.displayKeys ?? shortcut.keys).map((key) => {
    const labelKey = `shortcuts.keys.${key}`
    return te(labelKey) ? t(labelKey) : key
  })
}
</script>

<template>
  <div
    v-if="helpVisible"
    class="shortcuts-overlay"
    role="dialog"
    aria-modal="true"
    :aria-label="t('shortcuts.title')"
    @click.self="closeHelp"
  >
    <div class="shortcuts-panel">
      <header class="shortcuts-header">
        <span class="shortcuts-icon" :style="{ '--icon-url': `url(${keyboardIcon})` }" aria-hidden="true"></span>
        <h2>{{ t('shortcuts.title') }}</h2>
        <button
          type="button"
          class="shortcuts-close"
          :aria-label="t('shortcuts.close')"
          v-sound:cancel
          @click="closeHelp"
        >
          <span class="shortcuts-icon" :style="{ '--icon-url': `url(${xIcon})` }" aria-hidden="true"></span>
        </button>
      </header>

      <section
        v-for="group in helpGroups"
        :key="group.groupKey"
        class="shortcuts-group"
        :data-group="group.groupKey"
      >
        <h3>{{ t(group.groupKey) }}</h3>
        <ul>
          <li
            v-for="shortcut in group.shortcuts"
            :key="shortcut.id"
            class="shortcuts-row"
            :data-shortcut="shortcut.id"
          >
            <span class="shortcuts-label">{{ t(shortcut.labelKey) }}</span>
            <span class="shortcuts-keys">
              <kbd v-for="key in keycaps(shortcut)" :key="key">{{ key }}</kbd>
            </span>
          </li>
        </ul>
      </section>

      <p class="shortcuts-hint">{{ t('shortcuts.hint') }}</p>
    </div>
  </div>
</template>

<style scoped>
.shortcuts-overlay {
  position: fixed;
  inset: 0;
  z-index: 1100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(2px);
}

.shortcuts-panel {
  width: min(440px, 100%);
  max-height: calc(100vh - 32px);
  overflow-y: auto;
  box-sizing: border-box;
  padding: 18px 20px 14px;
  background: #1a1a1a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5);
  color: #ddd;
}

.shortcuts-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.shortcuts-header h2 {
  flex: 1;
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: #eee;
}

.shortcuts-icon {
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

.shortcuts-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  padding: 0;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  color: #aaa;
  cursor: pointer;
}

.shortcuts-close:hover {
  border-color: #444;
  color: #fff;
}

.shortcuts-group h3 {
  margin: 12px 0 6px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #86afe0;
}

.shortcuts-group ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

.shortcuts-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 5px 0;
  border-bottom: 1px solid #262626;
  font-size: 14px;
}

.shortcuts-keys {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 4px;
}

kbd {
  min-width: 22px;
  padding: 2px 6px;
  box-sizing: border-box;
  text-align: center;
  font-family: inherit;
  font-size: 12px;
  color: #eee;
  background: #2a2a2a;
  border: 1px solid #4a4a4a;
  border-bottom-width: 2px;
  border-radius: 4px;
}

.shortcuts-hint {
  margin: 12px 0 0;
  font-size: 12px;
  color: #888;
  text-align: center;
}
</style>
