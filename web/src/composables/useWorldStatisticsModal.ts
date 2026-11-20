import { computed, ref, shallowRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { worldApi } from '@/api/modules/world'
import { createEmptyWorldStatistics } from '@/api/mappers/worldStatistics'
import { SHARED_UI_COLORS, SYSTEM_PANEL_THEMES } from '@/constants/uiColors'
import { useUiStore } from '@/stores/ui'
import type {
  WorldStatistics,
  WorldStatisticsBucket,
  WorldStatisticsDistributionKey,
} from '@/types/core'
import { logError } from '@/utils/appError'

export interface WorldStatisticsSection {
  key: WorldStatisticsDistributionKey
  title: string
  buckets: WorldStatisticsBucket[]
}

const DISTRIBUTION_ORDER: WorldStatisticsDistributionKey[] = ['sect', 'race', 'orthodoxy', 'alignment', 'gender']

export function useWorldStatisticsModal(show: () => boolean, close: () => void) {
  const { t } = useI18n()
  const uiStore = useUiStore()
  const theme = SYSTEM_PANEL_THEMES.worldStatistics
  const panelStyleVars = {
    '--panel-accent': theme.accent,
    '--panel-accent-strong': theme.accentStrong,
    '--panel-accent-soft': theme.accentSoft,
    '--panel-link': theme.link,
    '--panel-link-hover': theme.linkHover,
    '--panel-title': theme.title,
    '--panel-empty': theme.empty,
    '--panel-border': theme.border,
    '--panel-text-primary': SHARED_UI_COLORS.textPrimary,
    '--panel-text-secondary': SHARED_UI_COLORS.textSecondary,
    '--panel-text-muted': SHARED_UI_COLORS.textMuted,
  }

  const loading = ref(false)
  const statistics = shallowRef<WorldStatistics>(createEmptyWorldStatistics())
  let requestId = 0

  async function fetchStatistics() {
    const currentRequest = ++requestId
    loading.value = true
    try {
      const result = await worldApi.fetchWorldStatistics()
      if (currentRequest === requestId) {
        statistics.value = result
      }
    } catch (error) {
      if (currentRequest === requestId) {
        statistics.value = createEmptyWorldStatistics()
      }
      logError('WorldStatisticsModal fetch statistics', error)
    } finally {
      if (currentRequest === requestId) {
        loading.value = false
      }
    }
  }

  const realms = computed(() => statistics.value.realms)
  const distributionSections = computed<WorldStatisticsSection[]>(() => (
    DISTRIBUTION_ORDER.map((key) => ({
      key,
      title: t(`game.world_statistics.sections.${key}`),
      buckets: statistics.value.distributions[key],
    }))
  ))
  const deathReasons = computed(() => statistics.value.deceased.topReasons)

  function formatPercent(value: number): string {
    return t('game.world_statistics.percent_value', { value: value.toFixed(1) })
  }

  function formatNumber(value: number): string {
    return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(1)
  }

  function openAvatarInfo(id: string) {
    void uiStore.select('avatar', id)
    close()
  }

  watch(show, (isShown) => {
    if (isShown) {
      void fetchStatistics()
    }
  }, { immediate: true })

  return {
    loading,
    statistics,
    realms,
    distributionSections,
    deathReasons,
    panelStyleVars,
    formatPercent,
    formatNumber,
    openAvatarInfo,
    fetchStatistics,
  }
}
