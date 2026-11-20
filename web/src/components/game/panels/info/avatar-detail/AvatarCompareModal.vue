<script setup lang="ts">
import { NModal, NSpin } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useAvatarCompareModal } from '@/composables/useAvatarCompareModal'
import AvatarComparePicker from './AvatarComparePicker.vue'
import scaleIcon from '@/assets/icons/ui/lucide/scale.svg'
import swordsIcon from '@/assets/icons/ui/lucide/swords.svg'
import heartHandshakeIcon from '@/assets/icons/ui/lucide/heart-handshake.svg'

const props = defineProps<{
  show: boolean
  avatarId: string
  avatarName: string
}>()

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void
}>()

const { t } = useI18n()

function handleShowChange(value: boolean) {
  emit('update:show', value)
}

const {
  step,
  search,
  candidates,
  loadingList,
  listError,
  comparison,
  loadingComparison,
  comparisonError,
  rows,
  winChance,
  relationViews,
  selectOpponent,
  backToPicker,
  openAvatar,
} = useAvatarCompareModal(
  () => props.show,
  () => ({ id: props.avatarId, name: props.avatarName }),
  () => handleShowChange(false),
)

const key = (path: string) => `game.info_panel.avatar.compare.${path}`
</script>

<template>
  <n-modal
    :show="show"
    @update:show="handleShowChange"
    preset="card"
    :title="t(key('title'))"
    style="width: 760px; max-width: calc(100vw - 32px); max-height: 85vh; overflow-y: auto;"
  >
    <n-spin :show="loadingList || loadingComparison">
      <AvatarComparePicker
        v-if="step === 'pick'"
        v-model:search="search"
        :title="t(key('picker_title'), { name: avatarName })"
        :candidates="candidates"
        :placeholder="t(key('search_placeholder'))"
        :empty-text="t(key('no_candidates'))"
        :error-text="listError"
        :loading="loadingList"
        @select="selectOpponent"
      />

      <div v-else class="avatar-compare">
        <div class="compare-toolbar">
          <button type="button" class="back-btn" @click="backToPicker">{{ t(key('back')) }}</button>
        </div>

        <div v-if="comparisonError" class="compare-error">{{ comparisonError }}</div>

        <template v-else-if="comparison">
          <div class="compare-header">
            <a class="side-name side-a" @click="openAvatar(comparison.a.id)">{{ comparison.a.name }}</a>
            <span class="versus">
              <span class="section-icon" :style="{ '--icon-url': `url(${scaleIcon})` }" aria-hidden="true"></span>
              {{ t(key('vs')) }}
            </span>
            <a class="side-name side-b" @click="openAvatar(comparison.b.id)">{{ comparison.b.name }}</a>
          </div>

          <section v-if="winChance" class="section win-section">
            <div class="section-title">
              <span class="section-icon" :style="{ '--icon-url': `url(${swordsIcon})` }" aria-hidden="true"></span>
              {{ t(key('win_title')) }}
            </div>
            <div class="win-labels">
              <span class="win-value" :class="{ favored: winChance.favored === 'a' }" data-side="a">
                {{ t(key('win_percent'), { value: winChance.aPercent }) }}
              </span>
              <span class="win-value" :class="{ favored: winChance.favored === 'b' }" data-side="b">
                {{ t(key('win_percent'), { value: winChance.bPercent }) }}
              </span>
            </div>
            <div class="win-bar" role="img" :aria-label="t(key('win_title'))">
              <span class="win-fill win-fill-a" :style="{ width: `${winChance.aPercent}%` }"></span>
              <span class="win-fill win-fill-b" :style="{ width: `${winChance.bPercent}%` }"></span>
            </div>
            <div class="win-hint">{{ winChance.hint }}</div>
          </section>

          <table class="compare-table">
            <tbody>
              <tr v-for="row in rows" :key="row.key" :data-row="row.key">
                <td class="cell cell-a" :class="{ better: row.better === 'a' }">
                  <div class="cell-main">{{ row.a }}</div>
                  <div v-if="row.aSub" class="cell-sub">{{ row.aSub }}</div>
                </td>
                <th class="cell-label" scope="row">{{ row.label }}</th>
                <td class="cell cell-b" :class="{ better: row.better === 'b' }">
                  <div class="cell-main">{{ row.b }}</div>
                  <div v-if="row.bSub" class="cell-sub">{{ row.bSub }}</div>
                </td>
              </tr>
            </tbody>
          </table>

          <section class="section">
            <div class="section-title">
              <span class="section-icon" :style="{ '--icon-url': `url(${heartHandshakeIcon})` }" aria-hidden="true"></span>
              {{ t(key('relation_title')) }}
            </div>
            <div class="relation-grid">
              <div v-for="view in relationViews" :key="view.key" class="relation-card" :data-relation="view.key">
                <div class="relation-heading">{{ view.title }}</div>
                <div class="relation-labels">{{ view.relation.labels.join(' / ') || t(key('none')) }}</div>
                <div class="relation-sub">{{ t(key('friendliness'), { value: view.relation.friendliness }) }}</div>
              </div>
            </div>
          </section>
        </template>
      </div>
    </n-spin>
  </n-modal>
</template>

<style scoped>
.avatar-compare {
  display: flex;
  flex-direction: column;
  gap: 14px;
  --side-a: #78b6ff;
  --side-b: #e1ab52;
  --better: #88bf8b;
}

.compare-toolbar {
  display: flex;
  justify-content: flex-end;
}

.back-btn {
  padding: 4px 10px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.05);
  color: #c8c4ba;
  font-size: 12px;
  cursor: pointer;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.compare-error {
  color: #d48370;
  font-size: 13px;
}

.compare-header {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
  font-size: 16px;
  font-weight: 700;
}

.side-name {
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.side-name:hover {
  text-decoration: underline;
}

.side-a {
  color: var(--side-a);
  text-align: right;
}

.side-b {
  color: var(--side-b);
}

.versus {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #90897c;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #c8c4ba;
  border-bottom: 1px solid #33302b;
  padding-bottom: 4px;
}

.section-icon {
  display: inline-block;
  width: 1em;
  height: 1em;
  flex-shrink: 0;
  background-color: currentColor;
  -webkit-mask: var(--icon-url) center / contain no-repeat;
  mask: var(--icon-url) center / contain no-repeat;
}

.win-labels {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
  color: #c8c4ba;
}

.win-value.favored {
  font-weight: 700;
  color: var(--better);
}

.win-bar {
  display: flex;
  height: 12px;
  border-radius: 6px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.06);
}

.win-fill-a {
  background: var(--side-a);
}

.win-fill-b {
  background: var(--side-b);
}

.win-hint {
  font-size: 11px;
  color: #90897c;
}

.compare-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.compare-table tr + tr {
  border-top: 1px solid #2a2824;
}

.cell,
.cell-label {
  padding: 6px 8px;
  vertical-align: top;
}

.cell {
  width: 40%;
  color: #f3f1ec;
  overflow-wrap: anywhere;
}

.cell-a {
  text-align: right;
}

.cell.better {
  color: var(--better);
  font-weight: 700;
  background: rgba(136, 191, 139, 0.08);
}

.cell-label {
  width: 20%;
  text-align: center;
  font-weight: 400;
  font-size: 12px;
  color: #90897c;
  white-space: nowrap;
}

.cell-sub {
  font-size: 11px;
  font-weight: 400;
  color: #90897c;
}

.relation-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}

.relation-card {
  padding: 8px 10px;
  border: 1px solid #33302b;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.03);
}

.relation-heading {
  font-size: 12px;
  color: #90897c;
  margin-bottom: 4px;
}

.relation-labels {
  font-size: 13px;
  color: #f3f1ec;
}

.relation-sub {
  font-size: 11px;
  color: #90897c;
  margin-top: 2px;
}
</style>
