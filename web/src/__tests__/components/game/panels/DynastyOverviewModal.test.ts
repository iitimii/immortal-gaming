import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import DynastyOverviewModal from '@/components/game/panels/DynastyOverviewModal.vue'

const refreshDetailMock = vi.fn()
const selectMock = vi.fn()

vi.mock('naive-ui', () => ({
  NModal: {
    name: 'NModal',
    template: '<div v-if="show" class="n-modal"><slot /></div>',
    props: ['show', 'title', 'preset'],
  },
  NTag: {
    name: 'NTag',
    template: '<span class="n-tag"><slot /></span>',
    props: ['bordered', 'type', 'size'],
  },
  NSpin: {
    name: 'NSpin',
    template: '<div class="n-spin"><slot /></div>',
    props: ['show'],
  },
}))

vi.mock('@/stores/dynasty', () => ({
  useDynastyStore: () => ({
    detail: {
      overview: {
        name: 'Jin',
        title: 'Jin Dynasty',
        royal_surname: 'Sima',
        royal_house_name: 'House of Sima',
        desc: 'Rigid lineages, gentry given to pure conversation; the court prizes ritual and Confucian propriety.',
        effect_desc: '',
        is_low_magic: true,
        current_emperor: {
          name: 'Sima Chengan',
          surname: 'Sima',
          given_name: 'Chengan',
          age: 34,
          max_age: 67,
          is_mortal: true,
        },
      },
      summary: {
        officialCount: 2,
        topOfficialRankName: 'Provincial Governor',
      },
      officials: [
        {
          id: 'a-1',
          name: 'Wang Xuance',
          realm: 'Core Formation',
          officialRankName: 'Provincial Governor',
          officialRankKey: 'PROVINCE',
          courtReputation: 520,
          sectName: 'Taiyi Sect',
        },
        {
          id: 'a-2',
          name: 'Li Guanlan',
          realm: 'Foundation Establishment',
          officialRankName: 'County Magistrate',
          officialRankKey: 'COUNTY',
          courtReputation: 120,
          sectName: '',
        },
      ],
    },
    overview: {
      name: 'Jin',
      title: 'Jin Dynasty',
      royal_surname: 'Sima',
      royal_house_name: 'House of Sima',
      desc: 'Rigid lineages, gentry given to pure conversation; the court prizes ritual and Confucian propriety.',
      effect_desc: '',
      is_low_magic: true,
      current_emperor: {
        name: 'Sima Chengan',
        surname: 'Sima',
        given_name: 'Chengan',
        age: 34,
        max_age: 67,
        is_mortal: true,
      },
    },
    officials: [
      {
        id: 'a-1',
        name: 'Wang Xuance',
        realm: 'Core Formation',
        officialRankName: 'Provincial Governor',
        officialRankKey: 'PROVINCE',
        courtReputation: 520,
        sectName: 'Taiyi Sect',
      },
      {
        id: 'a-2',
        name: 'Li Guanlan',
        realm: 'Foundation Establishment',
        officialRankName: 'County Magistrate',
        officialRankKey: 'COUNTY',
        courtReputation: 120,
        sectName: '',
      },
    ],
    summary: {
      officialCount: 2,
      topOfficialRankName: 'Provincial Governor',
    },
    isLoading: false,
    isLoaded: true,
    refreshDetail: refreshDetailMock,
    refreshOverview: refreshDetailMock,
  }),
}))

vi.mock('@/stores/ui', () => ({
  useUiStore: () => ({
    select: selectMock,
  }),
}))

describe('DynastyOverviewModal', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  function createWrapper(show = true) {
    const i18n = createI18n({
      legacy: false,
      locale: 'en-US',
      messages: {
        'en-US': {
          game: {
            dynasty: {
              title: 'Dynasty',
              name: 'Dynasty Name',
              royal_house: 'Royal House',
              style_tag: 'Dynasty Style',
              official_preference: 'Official Preference',
              effect: 'Dynasty Effect',
              effect_empty: 'No dynasty effect yet. This will be filled in after the official system and later logic are added.',
              low_magic: 'Mortal Dynasty',
              empty: 'No dynasty data',
              emperor: {
                title: 'Current Emperor',
                name: 'Name',
                age: 'Age',
                lifespan: 'Lifespan',
                identity: 'Identity',
                mortal: 'Mortal',
                empty: 'No emperor data',
              },
              summary: {
                title: 'Dynasty Overview',
              },
              officials: {
                title: 'Court Officials',
                count: '{count} total',
                empty: 'No court cultivators yet',
                realm: 'Realm',
                court_reputation: 'Court Reputation',
                sect: 'Affiliation',
                rogue: 'Rogue Cultivator',
              },
            },
          },
          common: {
            none: 'None',
          },
          realms: {
            FOUNDATION_ESTABLISHMENT: 'Foundation Establishment',
            CORE_FORMATION: 'Core Formation',
          },
        },
      },
    })

    return mount(DynastyOverviewModal, {
      props: { show },
      global: {
        plugins: [i18n],
      },
    })
  }

  it('fetches overview when opened', async () => {
    const wrapper = createWrapper(false)
    await wrapper.setProps({ show: true })
    expect(refreshDetailMock).toHaveBeenCalled()
  })

  it('fetches overview when initially mounted open', () => {
    createWrapper(true)
    expect(refreshDetailMock).toHaveBeenCalled()
  })

  it('renders dynasty summary', () => {
    const wrapper = createWrapper(true)
    const text = wrapper.text()
    expect(text).toContain('Jin Dynasty')
    expect(text).toContain('House of Sima')
    expect(text).toContain('Sima Chengan')
    expect(text).toContain('34')
    expect(text).toContain('67')
    expect(text).toContain('Rigid lineages')
    expect(text).toContain('Mortal Dynasty')
    expect(text).toContain('No dynasty effect yet')
    expect(text).toContain('Court Officials')
    expect(text).toContain('Wang Xuance')
    expect(text).toContain('Li Guanlan')
    expect(text).toContain('Taiyi Sect')
    expect(text).toContain('Rogue Cultivator')
  })

  it('jumps to avatar detail when clicking an official row', async () => {
    const wrapper = createWrapper(true)
    await wrapper.get('.official-row').trigger('click')
    expect(selectMock).toHaveBeenCalledWith('avatar', 'a-1')
  })
})
