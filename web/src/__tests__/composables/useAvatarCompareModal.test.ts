import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, nextTick, ref } from 'vue'

const mocks = vi.hoisted(() => ({
  fetchAvatarList: vi.fn(),
  fetchAvatarComparison: vi.fn(),
  select: vi.fn(),
  logError: vi.fn(),
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string, params?: Record<string, unknown>) => (params ? `${key}:${JSON.stringify(params)}` : key),
  }),
}))

vi.mock('@/api/modules/avatar', () => ({
  avatarApi: {
    fetchAvatarList: mocks.fetchAvatarList,
    fetchAvatarComparison: mocks.fetchAvatarComparison,
  },
}))

vi.mock('@/stores/ui', () => ({
  useUiStore: () => ({ select: mocks.select }),
}))

vi.mock('@/utils/appError', () => ({
  logError: mocks.logError,
  toErrorMessage: (error: unknown, fallback: string) => (error instanceof Error && error.message ? error.message : fallback),
}))

import { normalizeAvatarComparison } from '@/api/mappers/avatarCompare'
import { pickBetter, useAvatarCompareModal } from '@/composables/useAvatarCompareModal'
import { makeCompareDTO } from '../fixtures/avatarCompare'

const avatarList = [
  { id: 'a1', name: 'Elder Lan', sect_name: 'Azure Cloud Sect', realm: 'CORE_FORMATION', cultivation_display: 'Core Formation', gender: 'male', age: 120 },
  { id: 'b1', name: 'Wanderer Qiu', sect_name: 'Rogue Cultivator', realm: 'QI_REFINEMENT', cultivation_display: 'Qi Refinement', gender: 'male', age: 40 },
  { id: 'c1', name: 'Mei Ling', sect_name: 'Azure Cloud Sect', realm: 'FOUNDATION_ESTABLISHMENT', cultivation_display: 'Foundation Establishment', gender: 'female', age: 60 },
]

function mountComposable(initialShow: boolean, close = vi.fn()) {
  const show = ref(initialShow)
  let api!: ReturnType<typeof useAvatarCompareModal>
  const Host = defineComponent({
    setup() {
      api = useAvatarCompareModal(() => show.value, () => ({ id: 'a1', name: 'Elder Lan' }), close)
      return () => h('div')
    },
  })
  mount(Host)
  return { show, close, api: () => api }
}

// Global fake timers (see setup.ts) stall flushPromises; drain microtasks directly.
async function settle() {
  for (let i = 0; i < 5; i += 1) {
    await Promise.resolve()
  }
  await nextTick()
}

describe('pickBetter', () => {
  it('returns the strictly greater side and null on ties', () => {
    expect(pickBetter(3, 1)).toBe('a')
    expect(pickBetter(1, 3)).toBe('b')
    expect(pickBetter(2, 2)).toBeNull()
    expect(pickBetter(0, null)).toBe('a')
    expect(pickBetter(null, null)).toBeNull()
  })
})

describe('useAvatarCompareModal', () => {
  beforeEach(() => {
    mocks.fetchAvatarList.mockReset()
    mocks.fetchAvatarComparison.mockReset()
    mocks.select.mockReset()
    mocks.logError.mockReset()
  })

  it('loads the avatar list immediately when mounted shown and excludes the source avatar', async () => {
    mocks.fetchAvatarList.mockResolvedValue(avatarList)
    const { api } = mountComposable(true)

    expect(mocks.fetchAvatarList).toHaveBeenCalledTimes(1)
    await settle()

    expect(api().step.value).toBe('pick')
    expect(api().candidates.value.map((avatar) => avatar.id)).toEqual(['b1', 'c1'])
  })

  it('does not fetch while hidden and refetches every time it opens', async () => {
    mocks.fetchAvatarList.mockResolvedValue(avatarList)
    const { show } = mountComposable(false)
    expect(mocks.fetchAvatarList).not.toHaveBeenCalled()

    show.value = true
    await settle()
    show.value = false
    await settle()
    show.value = true
    await settle()

    expect(mocks.fetchAvatarList).toHaveBeenCalledTimes(2)
  })

  it('filters candidates by name, sect or realm case-insensitively', async () => {
    mocks.fetchAvatarList.mockResolvedValue(avatarList)
    const { api } = mountComposable(true)
    await settle()

    api().search.value = 'mei'
    expect(api().candidates.value.map((avatar) => avatar.id)).toEqual(['c1'])
    api().search.value = 'rogue'
    expect(api().candidates.value.map((avatar) => avatar.id)).toEqual(['b1'])
    api().search.value = 'qi refine'
    expect(api().candidates.value.map((avatar) => avatar.id)).toEqual(['b1'])
    api().search.value = 'lan'
    expect(api().candidates.value).toEqual([])
  })

  it('fetches the comparison for the selected opponent and builds highlighted rows', async () => {
    mocks.fetchAvatarList.mockResolvedValue(avatarList)
    mocks.fetchAvatarComparison.mockResolvedValue(normalizeAvatarComparison(makeCompareDTO()))
    const { api } = mountComposable(true)
    await settle()

    api().selectOpponent('b1')
    expect(api().step.value).toBe('compare')
    await settle()

    expect(mocks.fetchAvatarComparison).toHaveBeenCalledWith('a1', 'b1')
    const rows = Object.fromEntries(api().rows.value.map((row) => [row.key, row]))
    expect(rows.realm.better).toBe('a')
    expect(rows.battle_strength.better).toBe('a')
    expect(rows.hp).toMatchObject({ a: '250 / 300', b: '100 / 100', better: 'a' })
    expect(rows.lifespan.better).toBeNull()
    expect(rows.age.better).toBeNull()
    expect(rows.technique).toMatchObject({ a: 'Cloud Palm', aSub: 'Upper · Metal', better: 'a' })
    expect(rows.auxiliary).toMatchObject({ a: 'game.info_panel.avatar.compare.none', b: 'Jade Bell', better: 'b' })
    expect(rows.spirit_stones.better).toBe('b')
    expect(rows.sect).toMatchObject({ a: 'Azure Cloud Sect', aSub: 'Elder', b: 'game.info_panel.avatar.compare.rogue' })
    expect(rows.relations.better).toBeNull()

    expect(api().winChance.value).toMatchObject({ aPercent: 97.7, bPercent: 2.3, favored: 'a' })
    expect(api().relationViews.value[0].relation.labels).toEqual(['Sworn Brother', 'Friend'])
  })

  it('ignores selecting the source avatar and returns to the picker', async () => {
    mocks.fetchAvatarList.mockResolvedValue(avatarList)
    mocks.fetchAvatarComparison.mockResolvedValue(normalizeAvatarComparison(makeCompareDTO()))
    const { api } = mountComposable(true)
    await settle()

    api().selectOpponent('a1')
    expect(mocks.fetchAvatarComparison).not.toHaveBeenCalled()

    api().selectOpponent('b1')
    await settle()
    api().backToPicker()

    expect(api().step.value).toBe('pick')
    expect(api().comparison.value).toBeNull()
    expect(api().rows.value).toEqual([])
  })

  it('exposes the backend error message when the comparison fails', async () => {
    mocks.fetchAvatarList.mockResolvedValue(avatarList)
    mocks.fetchAvatarComparison.mockRejectedValue(new Error('Avatar is deceased and cannot be compared'))
    const { api } = mountComposable(true)
    await settle()

    api().selectOpponent('b1')
    await settle()

    expect(api().comparison.value).toBeNull()
    expect(api().comparisonError.value).toBe('Avatar is deceased and cannot be compared')
    expect(api().loadingComparison.value).toBe(false)
    expect(mocks.logError).toHaveBeenCalled()
  })

  it('opens the avatar detail and closes the modal', async () => {
    mocks.fetchAvatarList.mockResolvedValue([])
    const { api, close } = mountComposable(true)
    await settle()

    api().openAvatar('b1')

    expect(mocks.select).toHaveBeenCalledWith('avatar', 'b1')
    expect(close).toHaveBeenCalled()
  })
})
