import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import SectRelationsModal from '@/components/game/panels/SectRelationsModal.vue'

vi.mock('naive-ui', () => ({
  NModal: {
    name: 'NModal',
    template: '<div v-if="show" class="n-modal"><slot /></div>',
    props: ['show', 'title', 'preset'],
  },
  NTable: {
    name: 'NTable',
    template: '<table><slot /></table>',
    props: ['bordered', 'singleLine', 'size'],
  },
  NTag: {
    name: 'NTag',
    template: '<span class="n-tag"><slot /></span>',
    props: ['size', 'bordered'],
  },
  NSpin: {
    name: 'NSpin',
    template: '<div class="n-spin"><slot /></div>',
    props: ['show'],
  },
}))

vi.mock('@/api/modules/world', () => ({
  worldApi: {
    fetchInitialState: vi.fn(),
    fetchMap: vi.fn(),
    fetchPhenomenaList: vi.fn(),
    setPhenomenon: vi.fn(),
    fetchSectRelations: vi.fn(),
  },
}))

vi.mock('@/api', () => ({
  eventApi: {
    fetchEvents: vi.fn(),
  },
}))

const selectMock = vi.fn()
vi.mock('@/stores/ui', () => ({
  useUiStore: () => ({
    select: selectMock,
  }),
}))

import { worldApi } from '@/api/modules/world'

describe('SectRelationsModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const createWrapper = async () => {
    const flushPromises = () => Promise.resolve()
    const i18n = createI18n({
      legacy: false,
      locale: 'en-US',
      messages: {
        'en-US': {
          game: {
            sect_relations: {
              title: 'Sect Relations',
              sect_a: 'Sect A',
              sect_b: 'Sect B',
              status: 'Diplomatic Status',
              value: 'Relation Value',
              reasons: 'Reasons',
              empty: 'No relation data',
              status_war: 'At War',
              status_peace: 'Peace',
              duration_months: '{count} months',
              overlap_tiles: 'overlap {count} tiles',
              value_label_very_hostile: 'Very Hostile',
              value_label_hostile: 'Hostile',
              value_label_neutral: 'Neutral',
              value_label_friendly: 'Friendly',
              value_label_very_friendly: 'Very Friendly',
              reasons_map: {
                ALIGNMENT_OPPOSITE: 'Opposite alignment',
                ALIGNMENT_SAME: 'Same alignment',
                ORTHODOXY_DIFFERENT: 'Different orthodoxy',
                ORTHODOXY_SAME: 'Same orthodoxy',
                TERRITORY_CONFLICT: 'Territory conflict',
                WAR_STATE: 'State of war',
                PEACE_STATE: 'State of peace',
                LONG_PEACE: 'Long peace',
              },
            },
          },
        },
      },
    })

    vi.mocked(worldApi.fetchSectRelations).mockResolvedValue({
      relations: [
        {
          sect_a_id: 1,
          sect_a_name: 'Righteous Path Sect',
          sect_b_id: 2,
          sect_b_name: 'Demonic Path Sect',
          value: -32,
          diplomacy_status: 'war',
          diplomacy_duration_months: 18,
          reason_breakdown: [
            { reason: 'ALIGNMENT_OPPOSITE', delta: -40 },
            { reason: 'ORTHODOXY_SAME', delta: 10 },
            { reason: 'WAR_STATE', delta: -20, meta: { status: 'war', war_months: 18 } },
            { reason: 'TERRITORY_CONFLICT', delta: -2, meta: { border_contact_edges: 1 } },
          ],
        },
      ],
    })

    const wrapper = mount(SectRelationsModal, {
      props: { show: false },
      global: {
        plugins: [i18n],
      },
    })

    await wrapper.setProps({ show: true })
    await flushPromises()
    await wrapper.vm.$nextTick()
    return wrapper
  }

  it('renders reason and per-reason delta when data is loaded', async () => {
    const wrapper = await createWrapper()
    expect(wrapper.exists()).toBe(true)
    const text = wrapper.text()
    expect(text).toContain('Opposite alignment')
    expect(text).toContain('-40')
    expect(text).toContain('Same orthodoxy')
    expect(text).toContain('+10')
    expect(text).toContain('At War')
    expect(text).toContain('overlap 1 tiles')
  })

  it('does not render peace-state reason tag text when status column already shows peace', async () => {
    vi.mocked(worldApi.fetchSectRelations).mockResolvedValueOnce({
      relations: [
        {
          sect_a_id: 1,
          sect_a_name: 'Righteous Path Sect',
          sect_b_id: 2,
          sect_b_name: 'Qingxu Sect',
          value: 12,
          diplomacy_status: 'peace',
          diplomacy_duration_months: 16,
          reason_breakdown: [
            { reason: 'PEACE_STATE', delta: 0, meta: { status: 'peace', peace_months: 16 } },
            { reason: 'LONG_PEACE', delta: 1, meta: { status: 'peace', peace_months: 16 } },
          ],
        },
      ],
    })

    const wrapper = await createWrapper()
    const text = wrapper.text()
    expect(text).toContain('Peace')
    expect(text).toContain('Long peace')
    expect(text).not.toContain('State of peace')
    expect(text).not.toContain('Long peace (16 months)')
  })
})
