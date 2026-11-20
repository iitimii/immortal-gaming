import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach } from 'vitest'
import RegionDetail from '@/components/game/panels/info/RegionDetail.vue'
import { createPinia, setActivePinia } from 'pinia'
import { createI18n } from 'vue-i18n'

describe('RegionDetail', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should render successfully', () => {
    const i18n = createI18n({
      legacy: false,
      locale: 'en-US',
      messages: {
        'en-US': {
          game: {
            population: 'Population',
            mortal_system: {
              population_ratio_value: '{current} / {capacity}',
            },
            info_panel: {
              region: {
                type_explanations: {
                  city: 'City description',
                  ruin: 'Ruin description',
                  cave: 'Cave dwelling description',
                  sect: 'Sect description',
                  normal: 'Normal region description',
                },
              },
            },
          },
        },
      },
    })

    const wrapper = mount(RegionDetail, {
      props: {
        data: {
          id: '1',
          name: 'Test City',
          type: 'city',
          type_name: 'Test',
          desc: 'Test Desc',
          animals: [],
          plants: [],
          lodes: [],
          population: 120,
          population_capacity: 200,
        }
      },
      global: {
        plugins: [createPinia(), i18n],
        stubs: {
          EntityRow: true,
          RelationRow: true,
          SecondaryPopup: true,
        }
      }
    })

    expect(wrapper.exists()).toBe(true)
    expect(wrapper.text()).toContain('Population')
    expect(wrapper.text()).toContain('1.2M / 2M')
  })
})
