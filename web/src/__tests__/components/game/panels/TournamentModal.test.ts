import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import TournamentModal from '@/components/game/panels/TournamentModal.vue'

const fetchRankingsMock = vi.fn()

vi.mock('naive-ui', () => ({
  NModal: {
    name: 'NModal',
    template: '<div v-if="show"><slot /></div>',
    props: ['show'],
  },
  NSpin: {
    name: 'NSpin',
    template: '<div><slot /></div>',
    props: ['show'],
  },
  NEmpty: {
    name: 'NEmpty',
    template: '<div class="empty">{{ description }}</div>',
    props: ['description'],
  },
}))

vi.mock('@/stores/world', () => ({
  useWorldStore: () => ({ year: 100 }),
}))

vi.mock('@/stores/ui', () => ({
  useUiStore: () => ({ select: vi.fn() }),
}))

vi.mock('@/composables/useWorldOverviewData', () => ({
  useWorldOverviewData: () => ({
    loading: { value: false },
    rankings: {
      value: {
        heaven: [],
        earth: [],
        human: [],
        sect: [],
        tournament: {
          next_year: 120,
          heaven_first: null,
          earth_first: null,
          human_first: null,
        },
      },
    },
    fetchRankings: fetchRankingsMock,
  }),
}))

const i18n = createI18n({
  legacy: false,
  locale: 'en-US',
  messages: {
    'en-US': {
      game: {
        ranking: {
          tournament_title: 'World Martial Tournament',
          tournament_next: 'In {years} years',
          heaven_first: 'Heaven Ranking #1',
          earth_first: 'Earth Ranking #1',
          human_first: 'Human Ranking #1',
          empty: 'No data',
        },
      },
    },
  },
})

describe('TournamentModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches rankings when initially mounted open', () => {
    mount(TournamentModal, {
      props: { show: true },
      global: {
        plugins: [i18n],
      },
    })

    expect(fetchRankingsMock).toHaveBeenCalledTimes(1)
  })
})
