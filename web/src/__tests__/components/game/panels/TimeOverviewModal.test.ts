import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { nextTick } from 'vue'
import TimeOverviewModal from '@/components/game/panels/TimeOverviewModal.vue'

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

vi.mock('@/api/modules/world', () => ({
  worldApi: {
    fetchRankings: vi.fn(),
    fetchSectRelations: vi.fn(),
  },
}))

const worldStoreMock = {
  year: 103,
  month: 5,
  elapsedMonths: 29,
  currentPhenomenon: { id: 1, name: 'Spirit Tide', rarity: 'SR' },
}

vi.mock('@/stores/world', () => ({
  useWorldStore: () => worldStoreMock,
}))

import { worldApi } from '@/api/modules/world'

describe('TimeOverviewModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    worldStoreMock.year = 103
    worldStoreMock.month = 5
    worldStoreMock.elapsedMonths = 29
    worldStoreMock.currentPhenomenon = { id: 1, name: 'Spirit Tide', rarity: 'SR' }
  })

  function createWrapper() {
    const i18n = createI18n({
      legacy: false,
      locale: 'en-US',
      messages: {
        'en-US': {
          game: {
            status_bar: {
              time: {
                title: 'Time Overview',
                current_date: 'Current Date',
                current_date_value: 'Year {year}, Month {month}',
                elapsed: 'Run Duration',
                elapsed_months_only: 'Running for {months} months',
                elapsed_years_only: 'Running for {years} years',
                elapsed_years_months: 'Running for {years} years and {months} months',
                phenomenon: 'Current Phenomenon',
                no_phenomenon: 'No current phenomenon',
                tournament: 'Next Tournament',
                no_tournament: 'No tournament info available',
                sect_war: 'Sect Wars',
                war_active: '{count} sect war(s) currently active',
                war_none: 'No sect wars at the moment',
              },
            },
            ranking: {
              tournament_next: 'Next tournament in {years} years',
            },
          },
        },
      },
    })

    return mount(TimeOverviewModal, {
      props: { show: false },
      global: {
        plugins: [i18n],
      },
    })
  }

  it('renders the five overview items after loading data', async () => {
    vi.mocked(worldApi.fetchRankings).mockResolvedValue({
      heaven: [],
      earth: [],
      human: [],
      sect: [],
      tournament: { next_year: 110 },
    })
    vi.mocked(worldApi.fetchSectRelations).mockResolvedValue({
      relations: [
        {
          sect_a_id: 1,
          sect_a_name: 'Qingyun Sect',
          sect_b_id: 2,
          sect_b_name: 'Crimson Flame Sect',
          value: -30,
          diplomacy_status: 'war',
          diplomacy_duration_months: 12,
          reason_breakdown: [],
        },
        {
          sect_a_id: 3,
          sect_a_name: 'Xuanxin Sect',
          sect_b_id: 4,
          sect_b_name: 'Beidou Sect',
          value: 20,
          diplomacy_status: 'peace',
          diplomacy_duration_months: 8,
          reason_breakdown: [],
        },
      ],
    })

    const wrapper = createWrapper()
    await wrapper.setProps({ show: true })
    await Promise.resolve()
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('Year 103, Month 5')
    expect(text).toContain('Running for 2 years and 5 months')
    expect(text).toContain('Spirit Tide')
    expect(text).toContain('Next tournament in 7 years')
    expect(text).toContain('1 sect war(s) currently active')
  })

  it('shows empty-style fallback text when no phenomenon or no war exists', async () => {
    worldStoreMock.currentPhenomenon = null
    vi.mocked(worldApi.fetchRankings).mockResolvedValue({
      heaven: [],
      earth: [],
      human: [],
      sect: [],
    })
    vi.mocked(worldApi.fetchSectRelations).mockResolvedValue({
      relations: [],
    })

    const wrapper = createWrapper()
    await wrapper.setProps({ show: true })
    await Promise.resolve()
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('No current phenomenon')
    expect(text).toContain('No tournament info available')
    expect(text).toContain('No sect wars at the moment')
  })
})
