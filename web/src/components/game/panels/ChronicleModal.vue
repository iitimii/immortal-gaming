<script setup lang="ts">
import { NModal, NSpin } from 'naive-ui'
import { useI18n } from 'vue-i18n'

import { useChronicleModal } from '@/composables/useChronicleModal'
import milestoneIcon from '@/assets/icons/ui/lucide/milestone.svg'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void
}>()

const { t } = useI18n()

function handleShowChange(value: boolean) {
  emit('update:show', value)
}

const {
  loading,
  loaded,
  chronicle,
  achieved,
  pending,
  progress,
  panelStyleVars,
  openAvatar,
} = useChronicleModal(() => props.show, () => handleShowChange(false))
</script>

<template>
  <n-modal
    :show="show"
    @update:show="handleShowChange"
    preset="card"
    :title="t('game.chronicle.title')"
    style="width: 760px; max-height: 82vh; overflow-y: auto;"
  >
    <div class="chronicle-panel" :style="panelStyleVars">
      <div class="panel-caption">
        <span class="caption-icon" :style="{ '--icon-url': `url(${milestoneIcon})` }" aria-hidden="true"></span>
        <span>{{ t('game.chronicle.caption') }}</span>
        <span class="progress">{{ t('game.chronicle.progress', progress) }}</span>
      </div>
      <div v-if="chronicle.openedDateText" class="opened-since">
        {{ t('game.chronicle.opened_since', { date: chronicle.openedDateText }) }}
      </div>

      <n-spin :show="loading">
        <section class="chronicle-section">
          <h4>{{ t('game.chronicle.achieved') }}</h4>
          <div v-if="achieved.length === 0" class="empty">
            {{ loading && !loaded ? t('common.loading') : t('game.chronicle.empty') }}
          </div>
          <ol v-else class="timeline">
            <li v-for="item in achieved" :key="item.key" class="timeline-item" data-testid="chronicle-achieved">
              <div class="timeline-date">{{ item.dateText }}</div>
              <div class="timeline-body">
                <div class="timeline-title">{{ item.title }}</div>
                <div class="timeline-desc">{{ item.description }}</div>
                <div v-if="item.avatars.length || item.sects.length" class="timeline-refs">
                  <template v-for="avatar in item.avatars" :key="avatar.id">
                    <button
                      v-if="avatar.clickable"
                      type="button"
                      class="ref-link"
                      data-testid="chronicle-avatar-link"
                      @click="openAvatar(avatar)"
                    >
                      {{ avatar.name }}<span v-if="avatar.isDead" class="dead-tag">{{ t('game.deceased.title_short') }}</span>
                    </button>
                    <span v-else class="ref-text">{{ avatar.name }}</span>
                  </template>
                  <span v-for="sect in item.sects" :key="sect.id" class="ref-text">{{ sect.name }}</span>
                </div>
              </div>
            </li>
          </ol>
        </section>

        <section v-if="pending.length" class="chronicle-section">
          <h4>{{ t('game.chronicle.pending') }}</h4>
          <ul class="pending-list">
            <li v-for="item in pending" :key="item.key" class="pending-item" data-testid="chronicle-pending">
              <div class="pending-title">{{ item.title }}</div>
              <div class="pending-desc">{{ item.description }}</div>
            </li>
          </ul>
        </section>
      </n-spin>
    </div>
  </n-modal>
</template>

<style scoped>
.chronicle-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  color: var(--panel-text-primary);
}

.panel-caption {
  display: flex;
  align-items: center;
  gap: 7px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--panel-border);
  color: var(--panel-accent-strong);
  font-size: 13px;
}

.progress {
  margin-left: auto;
  color: var(--panel-text-secondary);
  white-space: nowrap;
}

.caption-icon {
  display: inline-block;
  width: 1em;
  height: 1em;
  background-color: currentColor;
  -webkit-mask-image: var(--icon-url);
  mask-image: var(--icon-url);
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-position: center;
  -webkit-mask-size: contain;
  mask-size: contain;
  flex-shrink: 0;
}

.opened-since {
  color: var(--panel-text-muted);
  font-size: 12px;
}

.chronicle-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.chronicle-section h4 {
  margin: 0;
  color: var(--panel-title);
  font-size: 14px;
}

.empty {
  color: var(--panel-empty);
  font-size: 13px;
  padding: 8px 0;
}

.timeline {
  list-style: none;
  margin: 0;
  padding: 0 0 0 14px;
  border-left: 2px solid var(--panel-border);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.timeline-item {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.timeline-item::before {
  content: '';
  position: absolute;
  left: -20px;
  top: 4px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--panel-accent);
  box-shadow: 0 0 0 3px var(--panel-accent-soft);
}

.timeline-date {
  color: var(--panel-text-muted);
  font-size: 12px;
}

.timeline-title {
  color: var(--panel-accent-strong);
  font-size: 15px;
  font-weight: 700;
}

.timeline-desc {
  color: var(--panel-text-secondary);
  font-size: 13px;
  line-height: 1.7;
}

.timeline-refs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
}

.ref-link {
  padding: 0;
  border: none;
  background: none;
  color: var(--panel-link);
  cursor: pointer;
  font: inherit;
}

.ref-link:hover {
  color: var(--panel-link-hover);
  text-decoration: underline;
}

.ref-text {
  color: var(--panel-text-muted);
}

.dead-tag {
  margin-left: 4px;
  color: var(--panel-text-muted);
}

.pending-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 8px;
}

.pending-item {
  padding: 8px 10px;
  border: 1px dashed var(--panel-border);
  border-radius: 6px;
  opacity: 0.55;
  filter: grayscale(1);
}

.pending-title {
  color: var(--panel-text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.pending-desc {
  color: var(--panel-text-muted);
  font-size: 12px;
  line-height: 1.6;
}
</style>
