<script setup lang="ts">
import { NModal, NSpin } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useWorldStatisticsModal } from '@/composables/useWorldStatisticsModal'
import StatisticsBarList from './StatisticsBarList.vue'
import chartBarIcon from '@/assets/icons/ui/lucide/chart-bar.svg'

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
  statistics,
  realms,
  distributionSections,
  deathReasons,
  panelStyleVars,
  formatPercent,
  formatNumber,
  openAvatarInfo,
} = useWorldStatisticsModal(() => props.show, () => handleShowChange(false))

function stageWidth(count: number): string {
  const total = statistics.value.livingCount
  return total > 0 ? `${(count / total) * 100}%` : '0%'
}
</script>

<template>
  <n-modal
    :show="show"
    @update:show="handleShowChange"
    preset="card"
    :title="t('game.world_statistics.title')"
    style="width: 900px; max-width: calc(100vw - 32px); max-height: 80vh; overflow-y: auto;"
  >
    <n-spin :show="loading">
      <div class="world-statistics" :style="panelStyleVars">
        <section class="section">
          <div class="section-title">
            <span class="section-title-icon" :style="{ '--icon-url': `url(${chartBarIcon})` }" aria-hidden="true"></span>
            {{ t('game.world_statistics.summary.title') }}
          </div>
          <div class="summary-grid">
            <div class="summary-card">
              <div class="summary-label">{{ t('game.world_statistics.summary.living') }}</div>
              <div class="summary-value">{{ statistics.livingCount }}</div>
            </div>
            <div class="summary-card">
              <div class="summary-label">{{ t('game.world_statistics.summary.deceased') }}</div>
              <div class="summary-value">{{ statistics.deceased.total }}</div>
            </div>
            <div class="summary-card">
              <div class="summary-label">{{ t('game.world_statistics.summary.average_age') }}</div>
              <div class="summary-value">
                {{ t('game.world_statistics.summary.age_value', { value: formatNumber(statistics.age.average) }) }}
              </div>
            </div>
            <div class="summary-card">
              <div class="summary-label">{{ t('game.world_statistics.summary.oldest') }}</div>
              <div v-if="statistics.age.oldest" class="summary-value summary-avatar">
                <a class="clickable-text oldest-link" @click="openAvatarInfo(statistics.age.oldest.id)">
                  {{ statistics.age.oldest.name }}
                </a>
                <span class="summary-sub">
                  {{ t('game.world_statistics.summary.age_value', { value: formatNumber(statistics.age.oldest.value) }) }}
                </span>
              </div>
              <div v-else class="summary-value summary-none">{{ t('game.world_statistics.summary.none') }}</div>
            </div>
            <div class="summary-card">
              <div class="summary-label">{{ t('game.world_statistics.summary.total_wealth') }}</div>
              <div class="summary-value">{{ formatNumber(statistics.wealth.total) }}</div>
            </div>
            <div class="summary-card">
              <div class="summary-label">{{ t('game.world_statistics.summary.average_wealth') }}</div>
              <div class="summary-value">{{ formatNumber(statistics.wealth.average) }}</div>
            </div>
            <div class="summary-card">
              <div class="summary-label">{{ t('game.world_statistics.summary.richest') }}</div>
              <div v-if="statistics.wealth.richest" class="summary-value summary-avatar">
                <a class="clickable-text richest-link" @click="openAvatarInfo(statistics.wealth.richest.id)">
                  {{ statistics.wealth.richest.name }}
                </a>
                <span class="summary-sub">
                  {{ t('game.world_statistics.summary.stones_value', { value: formatNumber(statistics.wealth.richest.value) }) }}
                </span>
              </div>
              <div v-else class="summary-value summary-none">{{ t('game.world_statistics.summary.none') }}</div>
            </div>
          </div>
        </section>

        <section class="section">
          <div class="section-title">{{ t('game.world_statistics.sections.realm') }}</div>
          <ul v-if="statistics.livingCount > 0" class="realm-list">
            <li v-for="realm in realms" :key="realm.id" class="realm-row" :data-realm-id="realm.id">
              <span class="realm-label">{{ realm.label }}</span>
              <span class="realm-track" aria-hidden="true">
                <span
                  v-for="(stage, index) in realm.stages"
                  :key="stage.id"
                  class="realm-stage"
                  :class="`stage-${index}`"
                  :style="{ width: stageWidth(stage.count) }"
                ></span>
              </span>
              <span class="realm-value">
                {{ realm.count }}
                <span class="realm-percent">{{ formatPercent(realm.percent) }}</span>
              </span>
              <span class="realm-stages">
                <span v-for="(stage, index) in realm.stages" :key="stage.id" class="realm-stage-item">
                  <span class="stage-swatch" :class="`stage-${index}`" aria-hidden="true"></span>
                  {{ stage.label }} {{ stage.count }}
                </span>
              </span>
            </li>
          </ul>
          <div v-else class="empty-text">{{ t('game.world_statistics.empty') }}</div>
        </section>

        <div class="distribution-grid">
          <section
            v-for="section in distributionSections"
            :key="section.key"
            class="section"
            :data-section="section.key"
          >
            <div class="section-title">{{ section.title }}</div>
            <StatisticsBarList
              :buckets="section.buckets"
              :empty-text="t('game.world_statistics.empty')"
              :format-percent="formatPercent"
            />
          </section>

          <section class="section" data-section="death_reasons">
            <div class="section-title">{{ t('game.world_statistics.sections.death_reasons') }}</div>
            <StatisticsBarList
              :buckets="deathReasons"
              :empty-text="t('game.world_statistics.empty')"
              :format-percent="formatPercent"
            />
          </section>
        </div>
      </div>
    </n-spin>
  </n-modal>
</template>

<style scoped>
.world-statistics {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  color: var(--panel-title);
  border-bottom: 1px solid var(--panel-border);
  padding-bottom: 6px;
}

.section-title-icon {
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

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
}

.summary-card {
  padding: 10px 12px;
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  background: var(--panel-accent-soft);
  min-width: 0;
}

.summary-label {
  font-size: 12px;
  color: var(--panel-text-secondary);
  margin-bottom: 6px;
}

.summary-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--panel-text-primary);
  font-variant-numeric: tabular-nums;
}

.summary-avatar {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 15px;
}

.summary-sub {
  font-size: 12px;
  font-weight: 400;
  color: var(--panel-text-muted);
}

.summary-none {
  color: var(--panel-empty);
}

.clickable-text {
  color: var(--panel-link);
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.clickable-text:hover {
  color: var(--panel-link-hover);
  text-decoration: underline;
}

.realm-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.realm-row {
  display: grid;
  grid-template-columns: minmax(110px, 22%) 1fr auto;
  align-items: center;
  column-gap: 8px;
  row-gap: 4px;
  font-size: 12px;
}

.realm-label {
  color: var(--panel-text-secondary);
}

.realm-track {
  display: flex;
  height: 10px;
  border-radius: 5px;
  background: var(--panel-accent-soft);
  overflow: hidden;
}

.realm-stage,
.stage-swatch {
  background: var(--panel-accent);
}

.stage-1 {
  opacity: 0.72;
}

.stage-2 {
  opacity: 0.46;
}

.realm-value {
  min-width: 72px;
  text-align: right;
  color: var(--panel-text-primary);
  font-variant-numeric: tabular-nums;
}

.realm-percent {
  margin-left: 4px;
  color: var(--panel-text-muted);
}

.realm-stages {
  grid-column: 2 / 4;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: var(--panel-text-muted);
  font-size: 11px;
}

.realm-stage-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.stage-swatch {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 2px;
}

.distribution-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 18px 24px;
}

.empty-text {
  font-size: 12px;
  color: var(--panel-empty);
}
</style>
