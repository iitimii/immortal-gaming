import { computed, ref, shallowRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { avatarApi } from '@/api/modules/avatar'
import { useUiStore } from '@/stores/ui'
import type { SimpleAvatarDTO } from '@/types/api'
import type { AvatarCompareItem, AvatarCompareSide, AvatarComparison } from '@/types/core'
import { logError, toErrorMessage } from '@/utils/appError'

export type CompareSideKey = 'a' | 'b'

export type CompareRowKey =
  | 'realm'
  | 'age'
  | 'lifespan'
  | 'hp'
  | 'battle_strength'
  | 'root'
  | 'orthodoxy'
  | 'sect'
  | 'alignment'
  | 'technique'
  | 'weapon'
  | 'auxiliary'
  | 'spirit_stones'
  | 'relations'

export interface CompareRow {
  key: CompareRowKey
  label: string
  a: string
  b: string
  aSub: string
  bSub: string
  better: CompareSideKey | null
}

export interface CompareSource {
  id: string
  name: string
}

/** Return which side holds the strictly greater score, or null on a tie / no score. */
export function pickBetter(a: number | null, b: number | null): CompareSideKey | null {
  const aScore = a ?? Number.NEGATIVE_INFINITY
  const bScore = b ?? Number.NEGATIVE_INFINITY
  if (aScore === bScore) return null
  return aScore > bScore ? 'a' : 'b'
}

export function toPercent(probability: number): number {
  return Math.round(probability * 1000) / 10
}

export function useAvatarCompareModal(
  show: () => boolean,
  source: () => CompareSource,
  close: () => void,
) {
  const { t } = useI18n()
  const uiStore = useUiStore()

  const avatarList = shallowRef<SimpleAvatarDTO[]>([])
  const search = ref('')
  const loadingList = ref(false)
  const listError = ref('')
  const opponentId = ref<string | null>(null)
  const comparison = shallowRef<AvatarComparison | null>(null)
  const loadingComparison = ref(false)
  const comparisonError = ref('')
  let listRequestId = 0
  let compareRequestId = 0

  const step = computed<'pick' | 'compare'>(() => (opponentId.value ? 'compare' : 'pick'))

  const candidates = computed(() => {
    const sourceId = source().id
    const query = search.value.trim().toLowerCase()
    return avatarList.value.filter((avatar) => {
      if (avatar.id === sourceId) return false
      if (!query) return true
      return [avatar.name, avatar.sect_name, avatar.cultivation_display ?? '']
        .some((field) => String(field ?? '').toLowerCase().includes(query))
    })
  })

  async function fetchAvatarList() {
    const requestId = ++listRequestId
    loadingList.value = true
    listError.value = ''
    try {
      const avatars = await avatarApi.fetchAvatarList()
      if (requestId === listRequestId) {
        avatarList.value = avatars
      }
    } catch (error) {
      if (requestId === listRequestId) {
        avatarList.value = []
        listError.value = toErrorMessage(error, t('game.info_panel.avatar.compare.list_failed'))
      }
      logError('AvatarCompareModal fetch avatar list', error)
    } finally {
      if (requestId === listRequestId) {
        loadingList.value = false
      }
    }
  }

  async function fetchComparison(bId: string) {
    const requestId = ++compareRequestId
    loadingComparison.value = true
    comparisonError.value = ''
    try {
      const result = await avatarApi.fetchAvatarComparison(source().id, bId)
      if (requestId === compareRequestId) {
        comparison.value = result
      }
    } catch (error) {
      if (requestId === compareRequestId) {
        comparison.value = null
        comparisonError.value = toErrorMessage(error, t('game.info_panel.avatar.compare.load_failed'))
      }
      logError('AvatarCompareModal fetch comparison', error)
    } finally {
      if (requestId === compareRequestId) {
        loadingComparison.value = false
      }
    }
  }

  function selectOpponent(id: string) {
    if (!id || id === source().id) return
    opponentId.value = id
    comparison.value = null
    void fetchComparison(id)
  }

  function backToPicker() {
    compareRequestId++
    opponentId.value = null
    comparison.value = null
    comparisonError.value = ''
    loadingComparison.value = false
  }

  function reset() {
    backToPicker()
    search.value = ''
  }

  function openAvatar(id: string) {
    void uiStore.select('avatar', id)
    close()
  }

  const none = () => t('game.info_panel.avatar.compare.none')

  function itemText(item: AvatarCompareItem | null): string {
    return item ? item.name : none()
  }

  function itemSub(item: AvatarCompareItem | null): string {
    if (!item) return ''
    return item.attribute ? `${item.grade} · ${item.attribute}` : item.grade
  }

  function buildRow(
    key: CompareRowKey,
    a: AvatarCompareSide,
    b: AvatarCompareSide,
    format: (side: AvatarCompareSide) => string,
    options: {
      sub?: (side: AvatarCompareSide) => string
      score?: (side: AvatarCompareSide) => number | null
    } = {},
  ): CompareRow {
    return {
      key,
      label: t(`game.info_panel.avatar.compare.rows.${key}`),
      a: format(a),
      b: format(b),
      aSub: options.sub ? options.sub(a) : '',
      bSub: options.sub ? options.sub(b) : '',
      better: options.score ? pickBetter(options.score(a), options.score(b)) : null,
    }
  }

  const rows = computed<CompareRow[]>(() => {
    const data = comparison.value
    if (!data) return []
    const { a, b } = data
    const gradeScore = (item: AvatarCompareItem | null) => (item ? item.gradeRank : null)
    return [
      buildRow('realm', a, b, (side) => side.cultivationDisplay || side.realm.label, {
        score: (side) => side.level,
      }),
      buildRow('battle_strength', a, b, (side) => side.battleStrength.toFixed(1), {
        score: (side) => side.battleStrength,
      }),
      buildRow('hp', a, b, (side) => `${side.hp.cur} / ${side.hp.max}`, {
        score: (side) => side.hp.max,
      }),
      buildRow('age', a, b, (side) => String(side.age)),
      buildRow('lifespan', a, b, (side) => String(side.lifespan), {
        score: (side) => side.lifespan,
      }),
      buildRow('root', a, b, (side) => side.root.label || none()),
      buildRow('orthodoxy', a, b, (side) => side.orthodoxy?.label || none()),
      buildRow('sect', a, b, (side) => side.sect?.name || t('game.info_panel.avatar.compare.rogue'), {
        sub: (side) => side.sect?.rank ?? '',
      }),
      buildRow('alignment', a, b, (side) => side.alignment?.label || none()),
      buildRow('technique', a, b, (side) => itemText(side.technique), {
        sub: (side) => itemSub(side.technique),
        score: (side) => gradeScore(side.technique),
      }),
      buildRow('weapon', a, b, (side) => itemText(side.weapon), {
        sub: (side) => itemSub(side.weapon),
        score: (side) => gradeScore(side.weapon),
      }),
      buildRow('auxiliary', a, b, (side) => itemText(side.auxiliary), {
        sub: (side) => itemSub(side.auxiliary),
        score: (side) => gradeScore(side.auxiliary),
      }),
      buildRow('spirit_stones', a, b, (side) => side.spiritStones.toLocaleString(), {
        score: (side) => side.spiritStones,
      }),
      buildRow('relations', a, b, (side) => String(side.relationCount)),
    ]
  })

  const winChance = computed(() => {
    const data = comparison.value
    if (!data) return null
    const aPercent = toPercent(data.battle.aWinProbability)
    return {
      aPercent,
      bPercent: Math.round((100 - aPercent) * 10) / 10,
      favored: pickBetter(data.battle.aWinProbability, data.battle.bWinProbability),
      hint: t('game.info_panel.avatar.compare.win_hint', {
        a: data.battle.aStrength.toFixed(1),
        b: data.battle.bStrength.toFixed(1),
      }),
    }
  })

  const relationViews = computed(() => {
    const data = comparison.value
    if (!data) return []
    return [
      {
        key: 'a_to_b',
        title: t('game.info_panel.avatar.compare.relation_view', { from: data.a.name, to: data.b.name }),
        relation: data.relation.aToB,
      },
      {
        key: 'b_to_a',
        title: t('game.info_panel.avatar.compare.relation_view', { from: data.b.name, to: data.a.name }),
        relation: data.relation.bToA,
      },
    ]
  })

  watch(show, (isShown) => {
    if (isShown) {
      reset()
      void fetchAvatarList()
    }
  }, { immediate: true })

  return {
    step,
    search,
    candidates,
    loadingList,
    listError,
    opponentId,
    comparison,
    loadingComparison,
    comparisonError,
    rows,
    winChance,
    relationViews,
    selectOpponent,
    backToPicker,
    openAvatar,
    fetchAvatarList,
  }
}
