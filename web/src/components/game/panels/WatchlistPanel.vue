<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useWatchlistPanel } from '@/composables/useWatchlistPanel'
import starIcon from '@/assets/icons/ui/lucide/star.svg'
import chevronRightIcon from '@/assets/icons/ui/lucide/chevron-right.svg'
import xIcon from '@/assets/icons/ui/lucide/x.svg'

const { t } = useI18n()
const {
  collapsed,
  items,
  count,
  toggleCollapsed,
  focusAvatar,
  unwatch,
} = useWatchlistPanel()
</script>

<template>
  <section class="watchlist-section" data-testid="watchlist-panel">
    <button
      class="watchlist-header"
      type="button"
      :aria-expanded="collapsed ? 'false' : 'true'"
      :title="collapsed ? t('game.watchlist.expand') : t('game.watchlist.collapse')"
      data-testid="watchlist-toggle"
      @click="toggleCollapsed"
    >
      <span
        class="watchlist-chevron"
        :class="{ 'is-open': !collapsed }"
        :style="{ '--icon-url': `url(${chevronRightIcon})` }"
        aria-hidden="true"
      ></span>
      <span class="watchlist-icon" :style="{ '--icon-url': `url(${starIcon})` }" aria-hidden="true"></span>
      <span class="watchlist-title">{{ t('game.watchlist.title') }}</span>
      <span class="watchlist-count" data-testid="watchlist-count">{{ count }}</span>
    </button>

    <div v-if="!collapsed" class="watchlist-body">
      <div v-if="items.length === 0" class="watchlist-empty">{{ t('game.watchlist.empty') }}</div>
      <ul v-else class="watchlist-list">
        <li
          v-for="item in items"
          :key="item.id"
          class="watchlist-row"
          :class="{ 'is-selected': item.selected, 'is-deceased': item.deceased }"
          data-testid="watchlist-row"
        >
          <button
            class="watchlist-focus"
            type="button"
            :title="item.name"
            data-testid="watchlist-focus"
            @click="focusAvatar(item.id)"
          >
            <span class="watchlist-dot" :style="{ backgroundColor: item.color }" aria-hidden="true"></span>
            <span class="watchlist-name">{{ item.name }}</span>
            <span v-if="item.realm" class="watchlist-realm">{{ item.realm }}</span>
            <span v-if="item.deceased" class="watchlist-deceased" data-testid="watchlist-deceased">
              {{ t('game.watchlist.deceased') }}
            </span>
          </button>
          <button
            class="watchlist-remove"
            type="button"
            :title="t('game.watchlist.unwatch', { name: item.name })"
            :aria-label="t('game.watchlist.unwatch', { name: item.name })"
            data-testid="watchlist-unwatch"
            v-sound:cancel
            @click="unwatch(item.id)"
          >
            <span class="watchlist-remove-icon" :style="{ '--icon-url': `url(${xIcon})` }" aria-hidden="true"></span>
          </button>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.watchlist-section {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-bottom: 1px solid #333;
  background: #1b1b1b;
}

.watchlist-header {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 6px 12px;
  border: none;
  background: #222;
  color: #ddd;
  font-size: 12px;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
}

.watchlist-header:hover {
  background: #262626;
}

.watchlist-chevron,
.watchlist-icon,
.watchlist-remove-icon {
  display: inline-block;
  flex-shrink: 0;
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

.watchlist-chevron {
  width: 12px;
  height: 12px;
  color: #888;
  transition: transform 0.15s ease;
}

.watchlist-chevron.is-open {
  transform: rotate(90deg);
}

.watchlist-icon {
  width: 13px;
  height: 13px;
  color: #f2c94c;
}

.watchlist-title {
  flex: 1;
  min-width: 0;
}

.watchlist-count {
  min-width: 18px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: #aaa;
  font-size: 11px;
  font-weight: 500;
  line-height: 16px;
  text-align: center;
}

.watchlist-body {
  max-height: 168px;
  overflow-y: auto;
}

.watchlist-empty {
  padding: 8px 12px;
  color: #666;
  font-size: 11px;
}

.watchlist-list {
  margin: 0;
  padding: 4px 0;
  list-style: none;
}

.watchlist-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 8px 0 4px;
}

.watchlist-row.is-selected {
  background: rgba(23, 125, 220, 0.14);
}

.watchlist-focus {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #ddd;
  font-size: 12px;
  text-align: left;
  cursor: pointer;
}

.watchlist-focus:hover {
  background: rgba(255, 255, 255, 0.05);
}

.watchlist-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.watchlist-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.watchlist-realm {
  flex-shrink: 0;
  max-width: 45%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #7fb6e0;
  font-size: 11px;
}

.watchlist-row.is-deceased .watchlist-name,
.watchlist-row.is-deceased .watchlist-realm {
  color: #777;
}

.watchlist-deceased {
  flex-shrink: 0;
  padding: 0 5px;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #999;
  font-size: 10px;
  line-height: 15px;
}

.watchlist-remove {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #777;
  cursor: pointer;
}

.watchlist-remove:hover {
  color: #eee;
  background: rgba(255, 255, 255, 0.08);
}

.watchlist-remove-icon {
  width: 12px;
  height: 12px;
}
</style>
