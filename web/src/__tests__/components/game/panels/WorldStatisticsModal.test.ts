import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, nextTick } from 'vue'

const mocks = vi.hoisted(() => ({
  fetchWorldStatistics: vi.fn(),
  select: vi.fn(),
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string, params?: Record<string, unknown>) => (params ? `${key}:${JSON.stringify(params)}` : key),
  }),
}))

vi.mock('naive-ui', () => ({
  NModal: defineComponent({
    name: 'NModal',
    props: ['show', 'preset', 'title'],
    emits: ['update:show'],
    setup(props, { slots }) {
      return () => (props.show ? h('div', { class: 'n-modal-stub' }, slots.default?.()) : null)
    },
  }),
  NSpin: defineComponent({
    name: 'NSpin',
    props: ['show'],
    setup(_, { slots }) {
      return () => h('div', { class: 'n-spin-stub' }, slots.default?.())
    },
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

import { createEmptyWorldStatistics, normalizeWorldStatistics } from '@/api/mappers/worldStatistics'
import WorldStatisticsModal from '@/components/game/panels/WorldStatisticsModal.vue'

const statistics = normalizeWorldStatistics({
  living_count: 4,
  realms: [
    {
      id: 'QI_REFINEMENT',
      label: 'Qi Refinement',
      count: 4,
      stages: [
        { id: 'EARLY_STAGE', label: 'Early Stage', count: 3 },
        { id: 'MIDDLE_STAGE', label: 'Middle Stage', count: 1 },
        { id: 'LATE_STAGE', label: 'Late Stage', count: 0 },
      ],
    },
    { id: 'NASCENT_SOUL', label: 'Nascent Soul', count: 0, stages: [] },
  ],
  distributions: {
    sect: [
      { id: '1', label: 'High Heaven Sword Sect', count: 3 },
      { id: 'rogue', label: 'Rogue Cultivator', count: 1 },
    ],
    race: [{ id: 'human', label: 'Human', count: 4 }],
    alignment: [{ id: 'RIGHTEOUS', label: 'Righteous', count: 4 }],
    gender: [{ id: 'male', label: 'Male', count: 4 }],
    orthodoxy: [{ id: 'dao', label: 'Dao', count: 4 }],
  },
  age: { average: 40, oldest: { id: 'elder-1', name: 'Elder Mo', value: 180 } },
  wealth: { total: 500, average: 125, richest: { id: 'rich-1', name: 'Merchant Qian', value: 400 } },
  deceased: { total: 2, top_reasons: [{ id: 'battle', label: 'Killed in battle', count: 2 }] },
})

// Global fake timers (see setup.ts) stall flushPromises; drain microtasks directly.
async function settle() {
  for (let i = 0; i < 5; i += 1) {
    await Promise.resolve()
  }
  await nextTick()
}

describe('WorldStatisticsModal', () => {
  beforeEach(() => {
    mocks.fetchWorldStatistics.mockReset()
    mocks.select.mockReset()
  })

  it('fetches on initial mount with show=true and renders bar charts', async () => {
    mocks.fetchWorldStatistics.mockResolvedValue(statistics)

    const wrapper = mount(WorldStatisticsModal, { props: { show: true } })
    expect(mocks.fetchWorldStatistics).toHaveBeenCalledTimes(1)
    await settle()

    const text = wrapper.text()
    expect(text).toContain('Elder Mo')
    expect(text).toContain('Merchant Qian')
    expect(text).toContain('Killed in battle')

    const realmRows = wrapper.findAll('.realm-row')
    expect(realmRows.map((row) => row.attributes('data-realm-id'))).toEqual(['QI_REFINEMENT', 'NASCENT_SOUL'])
    expect(realmRows[0].findAll('.realm-stage')[0].attributes('style')).toContain('width: 75%')

    const sectRows = wrapper.find('[data-section="sect"]').findAll('.bar-row')
    expect(sectRows).toHaveLength(2)
    expect(sectRows[1].attributes('data-bucket-id')).toBe('rogue')
    expect(sectRows[0].find('.bar-fill').attributes('style')).toContain('width: 75%')
    expect(sectRows[0].text()).toContain('game.world_statistics.percent_value:{"value":"75.0"}')

    const sectionKeys = wrapper.findAll('[data-section]').map((section) => section.attributes('data-section'))
    expect(sectionKeys).toEqual(['sect', 'race', 'orthodoxy', 'alignment', 'gender', 'death_reasons'])
  })

  it('opens the richest avatar detail and closes the modal', async () => {
    mocks.fetchWorldStatistics.mockResolvedValue(statistics)

    const wrapper = mount(WorldStatisticsModal, { props: { show: true } })
    await settle()

    await wrapper.find('.richest-link').trigger('click')

    expect(mocks.select).toHaveBeenCalledWith('avatar', 'rich-1')
    expect(wrapper.emitted('update:show')?.[0]).toEqual([false])
  })

  it('opens the oldest avatar detail', async () => {
    mocks.fetchWorldStatistics.mockResolvedValue(statistics)

    const wrapper = mount(WorldStatisticsModal, { props: { show: true } })
    await settle()

    await wrapper.find('.oldest-link').trigger('click')

    expect(mocks.select).toHaveBeenCalledWith('avatar', 'elder-1')
  })

  it('renders empty states for an empty world', async () => {
    mocks.fetchWorldStatistics.mockResolvedValue(createEmptyWorldStatistics())

    const wrapper = mount(WorldStatisticsModal, { props: { show: true } })
    await settle()

    expect(wrapper.find('.realm-row').exists()).toBe(false)
    expect(wrapper.find('.richest-link').exists()).toBe(false)
    expect(wrapper.text()).toContain('game.world_statistics.summary.none')
    expect(wrapper.findAll('.bar-empty')).toHaveLength(6)
  })
})
