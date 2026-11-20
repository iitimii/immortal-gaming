import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { createI18n } from 'vue-i18n'

import type { WorldMilestonesView } from '@/api/mappers/milestone'

const mocks = vi.hoisted(() => ({
  fetchWorldMilestones: vi.fn(),
  select: vi.fn(),
}))

vi.mock('naive-ui', () => ({
  NModal: {
    name: 'NModal',
    template: '<div v-if="show" class="n-modal"><slot /></div>',
    props: ['show', 'title', 'preset'],
  },
  NSpin: {
    name: 'NSpin',
    template: '<div class="n-spin"><slot /></div>',
    props: ['show'],
  },
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

import ChronicleModal from '@/components/game/panels/ChronicleModal.vue'

const view: WorldMilestonesView = {
  achieved: [
    {
      key: 'first_sworn_siblings',
      kind: 'sworn_siblings',
      title: 'First Sworn Siblings',
      description: 'Alpha and Beta swore the first oath.',
      monthStamp: 18,
      year: 2,
      month: 7,
      dateText: 'Year 2 Month 7',
      avatars: [
        { id: 'a-1', name: 'Alpha', clickable: true, isDead: false },
        { id: 'a-2', name: 'Beta', clickable: false, isDead: true },
      ],
      sects: [],
    },
  ],
  pending: [
    { key: 'first_sect_war', kind: 'sect_war', title: 'First Sect War', description: 'The first war.' },
    { key: 'first_age_100', kind: 'age', title: 'First to Live 100 Years', description: 'Long life.' },
  ],
  total: 3,
  openedDateText: 'Year 1 Month 1',
}

async function flush() {
  // Global fake timers are enabled in setup.ts, so drain microtasks instead of waiting on a timer.
  for (let i = 0; i < 5; i += 1) await Promise.resolve()
  await nextTick()
}

function createWrapper(show: boolean) {
  const i18n = createI18n({
    legacy: false,
    locale: 'en-US',
    messages: {
      'en-US': {
        common: { loading: 'Loading' },
        game: {
          deceased: { title_short: '(Dead)' },
          chronicle: {
            title: 'Chronicle of Firsts',
            caption: 'Caption',
            progress: '{achieved} / {total} recorded',
            opened_since: 'Kept since {date}',
            achieved: 'Recorded firsts',
            pending: 'Yet to happen',
            empty: 'Nothing yet',
          },
        },
      },
    },
  })

  return mount(ChronicleModal, {
    props: { show },
    global: { plugins: [i18n] },
  })
}

describe('ChronicleModal', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads on initial mount with show=true and renders the timeline', async () => {
    mocks.fetchWorldMilestones.mockResolvedValue(view)

    const wrapper = createWrapper(true)
    await flush()

    expect(mocks.fetchWorldMilestones).toHaveBeenCalledTimes(1)
    const achieved = wrapper.findAll('[data-testid="chronicle-achieved"]')
    expect(achieved).toHaveLength(1)
    expect(achieved[0].text()).toContain('Year 2 Month 7')
    expect(achieved[0].text()).toContain('First Sworn Siblings')
    expect(wrapper.findAll('[data-testid="chronicle-pending"]')).toHaveLength(2)
    expect(wrapper.text()).toContain('1 / 3 recorded')
    expect(wrapper.text()).toContain('Kept since Year 1 Month 1')
  })

  it('opens avatar detail when clicking an avatar name and closes the modal', async () => {
    mocks.fetchWorldMilestones.mockResolvedValue(view)

    const wrapper = createWrapper(true)
    await flush()

    const links = wrapper.findAll('[data-testid="chronicle-avatar-link"]')
    // Only avatars still known to the world are clickable.
    expect(links).toHaveLength(1)
    await links[0].trigger('click')

    expect(mocks.select).toHaveBeenCalledWith('avatar', 'a-1')
    expect(wrapper.emitted('update:show')?.[0]).toEqual([false])
  })

  it('shows the empty state when nothing has been recorded', async () => {
    mocks.fetchWorldMilestones.mockResolvedValue({ ...view, achieved: [] })

    const wrapper = createWrapper(true)
    await flush()

    expect(wrapper.text()).toContain('Nothing yet')
  })
})
