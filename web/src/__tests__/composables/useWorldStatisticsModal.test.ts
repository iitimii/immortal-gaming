import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, nextTick, ref } from 'vue'

const mocks = vi.hoisted(() => ({
  fetchWorldStatistics: vi.fn(),
  select: vi.fn(),
  logError: vi.fn(),
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string, params?: Record<string, unknown>) => (params ? `${key}:${JSON.stringify(params)}` : key),
  }),
}))

vi.mock('@/api/modules/world', () => ({
  worldApi: {
    fetchWorldStatistics: mocks.fetchWorldStatistics,
  },
}))

vi.mock('@/stores/ui', () => ({
  useUiStore: () => ({ select: mocks.select }),
}))

vi.mock('@/utils/appError', () => ({
  logError: mocks.logError,
}))

import { createEmptyWorldStatistics } from '@/api/mappers/worldStatistics'
import { useWorldStatisticsModal } from '@/composables/useWorldStatisticsModal'

function mountComposable(initialShow: boolean, close = vi.fn()) {
  const show = ref(initialShow)
  let api!: ReturnType<typeof useWorldStatisticsModal>
  const Host = defineComponent({
    setup() {
      api = useWorldStatisticsModal(() => show.value, close)
      return () => h('div')
    },
  })
  const wrapper = mount(Host)
  return { wrapper, show, close, api: () => api }
}

function makeStatistics() {
  const stats = createEmptyWorldStatistics()
  stats.livingCount = 2
  stats.distributions.sect = [{ id: 'rogue', label: 'Rogue Cultivator', count: 2, percent: 100 }]
  return stats
}

// Global fake timers (see setup.ts) stall flushPromises; drain microtasks directly.
async function settle() {
  for (let i = 0; i < 5; i += 1) {
    await Promise.resolve()
  }
  await nextTick()
}

describe('useWorldStatisticsModal', () => {
  beforeEach(() => {
    mocks.fetchWorldStatistics.mockReset()
    mocks.select.mockReset()
    mocks.logError.mockReset()
  })

  it('fetches immediately when mounted with show=true', async () => {
    mocks.fetchWorldStatistics.mockResolvedValue(makeStatistics())

    const { api } = mountComposable(true)
    expect(mocks.fetchWorldStatistics).toHaveBeenCalledTimes(1)
    expect(api().loading.value).toBe(true)

    await settle()

    expect(api().loading.value).toBe(false)
    expect(api().statistics.value.livingCount).toBe(2)
    const sectSection = api().distributionSections.value.find((section) => section.key === 'sect')
    expect(sectSection?.title).toBe('game.world_statistics.sections.sect')
    expect(sectSection?.buckets).toHaveLength(1)
  })

  it('does not fetch while hidden and fetches once shown', async () => {
    mocks.fetchWorldStatistics.mockResolvedValue(makeStatistics())

    const { show } = mountComposable(false)
    expect(mocks.fetchWorldStatistics).not.toHaveBeenCalled()

    show.value = true
    await nextTick()

    expect(mocks.fetchWorldStatistics).toHaveBeenCalledTimes(1)
  })

  it('resets to empty statistics and logs when the request fails', async () => {
    mocks.fetchWorldStatistics.mockRejectedValue(new Error('boom'))

    const { api } = mountComposable(true)
    await settle()

    expect(api().statistics.value).toEqual(createEmptyWorldStatistics())
    expect(api().loading.value).toBe(false)
    expect(mocks.logError).toHaveBeenCalled()
  })

  it('opens avatar detail and closes the modal', async () => {
    mocks.fetchWorldStatistics.mockResolvedValue(makeStatistics())
    const { api, close } = mountComposable(true)
    await settle()

    api().openAvatarInfo('avatar-1')

    expect(mocks.select).toHaveBeenCalledWith('avatar', 'avatar-1')
    expect(close).toHaveBeenCalled()
  })

  it('formats percentages and numbers', () => {
    mocks.fetchWorldStatistics.mockResolvedValue(makeStatistics())
    const { api } = mountComposable(false)

    expect(api().formatPercent(33.333)).toBe('game.world_statistics.percent_value:{"value":"33.3"}')
    expect(api().formatNumber(12.345)).toBe('12.3')
    expect(api().formatNumber(1200)).toBe((1200).toLocaleString())
  })
})
