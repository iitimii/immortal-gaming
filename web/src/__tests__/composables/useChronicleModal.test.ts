import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'

import type { WorldMilestonesView } from '@/api/mappers/milestone'

const mocks = vi.hoisted(() => ({
  fetchWorldMilestones: vi.fn(),
  select: vi.fn(),
}))

vi.mock('@/api/modules/milestone', () => ({
  milestoneApi: {
    fetchWorldMilestones: mocks.fetchWorldMilestones,
  },
}))

vi.mock('@/stores/ui', () => ({
  useUiStore: () => ({
    select: mocks.select,
  }),
}))

import { useChronicleModal } from '@/composables/useChronicleModal'

const view: WorldMilestonesView = {
  achieved: [
    {
      key: 'first_realm_core_formation',
      kind: 'realm',
      title: 'First to Reach Core Formation',
      description: 'Hero broke through.',
      monthStamp: 20,
      year: 2,
      month: 9,
      dateText: 'Year 2 Month 9',
      avatars: [{ id: 'a-1', name: 'Hero', clickable: true, isDead: false }],
      sects: [],
    },
  ],
  pending: [{ key: 'first_sect_war', kind: 'sect_war', title: 'First Sect War', description: 'War.' }],
  total: 2,
  openedDateText: 'Year 1 Month 1',
}

async function flush() {
  // Global fake timers are enabled in setup.ts, so drain microtasks instead of waiting on a timer.
  for (let i = 0; i < 5; i += 1) await Promise.resolve()
  await nextTick()
}

describe('useChronicleModal', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetches immediately when mounted already shown', async () => {
    mocks.fetchWorldMilestones.mockResolvedValue(view)
    const close = vi.fn()

    const modal = useChronicleModal(() => true, close)
    expect(mocks.fetchWorldMilestones).toHaveBeenCalledTimes(1)
    await flush()

    expect(modal.loaded.value).toBe(true)
    expect(modal.achieved.value).toHaveLength(1)
    expect(modal.pending.value).toHaveLength(1)
    expect(modal.progress.value).toEqual({ achieved: 1, total: 2 })
  })

  it('fetches again each time the modal is shown', async () => {
    mocks.fetchWorldMilestones.mockResolvedValue(view)
    const show = ref(false)

    useChronicleModal(() => show.value, vi.fn())
    expect(mocks.fetchWorldMilestones).not.toHaveBeenCalled()

    show.value = true
    await nextTick()
    expect(mocks.fetchWorldMilestones).toHaveBeenCalledTimes(1)
  })

  it('resets to an empty chronicle when the request fails', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    mocks.fetchWorldMilestones.mockRejectedValue(new Error('boom'))

    const modal = useChronicleModal(() => true, vi.fn())
    await flush()

    expect(modal.loaded.value).toBe(false)
    expect(modal.loading.value).toBe(false)
    expect(modal.achieved.value).toEqual([])
    consoleError.mockRestore()
  })

  it('opens avatar detail and closes only for clickable avatars', () => {
    mocks.fetchWorldMilestones.mockResolvedValue(view)
    const close = vi.fn()
    const modal = useChronicleModal(() => false, close)

    modal.openAvatar({ id: 'gone', name: 'Gone', clickable: false, isDead: true })
    expect(mocks.select).not.toHaveBeenCalled()
    expect(close).not.toHaveBeenCalled()

    modal.openAvatar({ id: 'a-1', name: 'Hero', clickable: true, isDead: false })
    expect(mocks.select).toHaveBeenCalledWith('avatar', 'a-1')
    expect(close).toHaveBeenCalledTimes(1)
  })
})
