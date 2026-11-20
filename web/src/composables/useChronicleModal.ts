import { computed, ref, shallowRef, watch } from 'vue'

import { milestoneApi } from '@/api/modules/milestone'
import type { MilestoneAvatarView, WorldMilestonesView } from '@/api/mappers/milestone'
import { SHARED_UI_COLORS, SYSTEM_PANEL_THEMES } from '@/constants/uiColors'
import { useUiStore } from '@/stores/ui'
import { logError } from '@/utils/appError'

const EMPTY_CHRONICLE: WorldMilestonesView = {
  achieved: [],
  pending: [],
  total: 0,
  openedDateText: '',
}

export function useChronicleModal(show: () => boolean, close: () => void) {
  const uiStore = useUiStore()
  const theme = SYSTEM_PANEL_THEMES.chronicle
  const panelStyleVars = {
    '--panel-accent': theme.accent,
    '--panel-accent-strong': theme.accentStrong,
    '--panel-accent-soft': theme.accentSoft,
    '--panel-title': theme.title,
    '--panel-empty': theme.empty,
    '--panel-border': theme.border,
    '--panel-link': SHARED_UI_COLORS.linkBlue,
    '--panel-link-hover': SHARED_UI_COLORS.linkBlueHover,
    '--panel-text-primary': SHARED_UI_COLORS.textPrimary,
    '--panel-text-secondary': SHARED_UI_COLORS.textSecondary,
    '--panel-text-muted': SHARED_UI_COLORS.textMuted,
  }

  const loading = ref(false)
  const loaded = ref(false)
  const chronicle = shallowRef<WorldMilestonesView>(EMPTY_CHRONICLE)
  let requestId = 0

  const achieved = computed(() => chronicle.value.achieved)
  const pending = computed(() => chronicle.value.pending)
  const progress = computed(() => ({
    achieved: chronicle.value.achieved.length,
    total: chronicle.value.total,
  }))

  async function fetchChronicle() {
    const currentRequestId = ++requestId
    loading.value = true
    try {
      const data = await milestoneApi.fetchWorldMilestones()
      if (currentRequestId !== requestId) return
      chronicle.value = data
      loaded.value = true
    } catch (error) {
      if (currentRequestId !== requestId) return
      logError('ChronicleModal fetch milestones', error)
      chronicle.value = EMPTY_CHRONICLE
      loaded.value = false
    } finally {
      if (currentRequestId === requestId) {
        loading.value = false
      }
    }
  }

  function openAvatar(avatar: MilestoneAvatarView) {
    if (!avatar.clickable) return
    void uiStore.select('avatar', avatar.id)
    close()
  }

  watch(show, (isShown) => {
    if (isShown) {
      void fetchChronicle()
    }
  }, { immediate: true })

  return {
    loading,
    loaded,
    chronicle,
    achieved,
    pending,
    progress,
    panelStyleVars,
    fetchChronicle,
    openAvatar,
  }
}
