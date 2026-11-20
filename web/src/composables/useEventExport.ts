import { computed, ref, watch } from 'vue'
import type { Ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { eventApi } from '@/api/modules/event'
import { useAvatarStore } from '@/stores/avatar'
import type { EventExportFormat, EventExportParams } from '@/types/api'
import { logError, toErrorMessage } from '@/utils/appError'
import { message } from '@/utils/discreteApi'
import { saveBlobAsFile } from '@/utils/fileDownload'

export type EventExportScope = 'all' | 'avatar' | 'major'

const FALLBACK_EXTENSIONS: Record<EventExportFormat, string> = {
  markdown: 'md',
  json: 'json',
}

/**
 * Export menu state for the event panel.
 *
 * @param avatarId the avatar the panel is currently filtered to ('' when unfiltered).
 */
export function useEventExport(avatarId: Ref<string>) {
  const { t } = useI18n()
  const avatarStore = useAvatarStore()

  const showMenu = ref(false)
  const exportFormat = ref<EventExportFormat>('markdown')
  const exportScope = ref<EventExportScope>('all')
  const exporting = ref(false)

  const avatarName = computed(() => {
    if (!avatarId.value) return ''
    const avatar = avatarStore.avatarList.find(item => item.id === avatarId.value)
    return avatar?.name ?? avatarId.value
  })

  const formatOptions = computed(() => [
    { label: t('game.event_panel.export_format_markdown'), value: 'markdown' as const },
    { label: t('game.event_panel.export_format_json'), value: 'json' as const },
  ])

  const scopeOptions = computed(() => {
    const options: { label: string; value: EventExportScope }[] = [
      { label: t('game.event_panel.export_scope_all'), value: 'all' },
    ]
    if (avatarId.value) {
      options.push({
        label: t('game.event_panel.export_scope_avatar', { avatar: avatarName.value }),
        value: 'avatar',
      })
    }
    options.push({ label: t('game.event_panel.export_scope_major'), value: 'major' })
    return options
  })

  // Follow the panel filter: default to the filtered avatar, and drop the
  // avatar scope once the panel is no longer filtered.
  watch(
    avatarId,
    (id) => {
      if (id) {
        exportScope.value = 'avatar'
      } else if (exportScope.value === 'avatar') {
        exportScope.value = 'all'
      }
    },
    { immediate: true },
  )

  function buildExportParams(): EventExportParams {
    const params: EventExportParams = { format: exportFormat.value }
    if (exportScope.value === 'avatar' && avatarId.value) {
      params.avatar_id = avatarId.value
    } else if (exportScope.value === 'major') {
      params.major_only = true
    }
    return params
  }

  async function runExport() {
    if (exporting.value) return
    exporting.value = true
    try {
      const file = await eventApi.downloadEventExport(buildExportParams())
      const filename = file.filename ?? `chronicle.${FALLBACK_EXTENSIONS[exportFormat.value]}`
      saveBlobAsFile(file.blob, filename)
      showMenu.value = false
    } catch (error) {
      logError('EventExport', error)
      message.error(t('game.event_panel.export_failed', { error: toErrorMessage(error) }))
    } finally {
      exporting.value = false
    }
  }

  return {
    showMenu,
    exportFormat,
    exportScope,
    exporting,
    formatOptions,
    scopeOptions,
    buildExportParams,
    runExport,
  }
}
