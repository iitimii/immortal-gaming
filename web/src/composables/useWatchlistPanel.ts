import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { AvatarDetail } from '@/types/core'
import { useAvatarStore } from '@/stores/avatar'
import { useUiStore } from '@/stores/ui'
import { useWatchlistStore } from '@/stores/watchlist'
import { avatarIdToColor } from '@/utils/eventHelper'
import { formatCultivationText } from '@/utils/cultivationText'

export interface WatchlistItemView {
  id: string
  name: string
  realm: string
  deceased: boolean
  color: string
  selected: boolean
}

/** Sidebar watchlist: derived rows plus focus/unwatch actions. */
export function useWatchlistPanel() {
  const { t } = useI18n()
  const watchlistStore = useWatchlistStore()
  const avatarStore = useAvatarStore()
  const uiStore = useUiStore()

  const collapsed = ref(false)

  const items = computed<WatchlistItemView[]>(() => {
    const selected = uiStore.selectedTarget
    return watchlistStore.entries.map(entry => {
      const live = avatarStore.avatars.get(entry.id)
      return {
        id: entry.id,
        name: live?.name || entry.name || entry.id,
        realm: live
          ? live.cultivation_display || formatCultivationText(live.realm, t)
          : entry.realm,
        deceased: live ? live.is_dead === true : entry.deceased,
        color: avatarIdToColor(entry.id),
        selected: selected?.type === 'avatar' && selected.id === entry.id,
      }
    })
  })

  const count = computed(() => watchlistStore.count)

  function toggleCollapsed() {
    collapsed.value = !collapsed.value
  }

  function focusAvatar(id: string) {
    void uiStore.select('avatar', id)
  }

  function unwatch(id: string) {
    watchlistStore.remove(id)
  }

  return {
    collapsed,
    items,
    count,
    toggleCollapsed,
    focusAvatar,
    unwatch,
  }
}

/** Star toggle state for the avatar detail header. */
export function useAvatarWatchToggle(data: () => AvatarDetail, realmText: () => string) {
  const watchlistStore = useWatchlistStore()

  const isWatched = computed(() => watchlistStore.isWatched(data().id))

  function toggleWatch() {
    const detail = data()
    watchlistStore.toggle(detail.id, {
      name: detail.name,
      realm: realmText(),
      deceased: detail.is_dead === true,
    })
  }

  return { isWatched, toggleWatch }
}
