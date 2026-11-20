import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'
import EntityDetailCard from '@/components/game/panels/info/components/EntityDetailCard.vue'

function buildI18n() {
  return createI18n({
    legacy: false,
    locale: 'en-US',
    messages: {
      'en-US': {
        game: {
          info_panel: {
            popup: {
              effect: 'Effect',
              drops: 'Drops',
              hq: 'Headquarters',
            },
          },
        },
        technique_grades: {
          UPPER: 'Upper Grade',
        },
      },
    },
  })
}

describe('EntityDetailCard', () => {
  it('renders epic badge style for rarity-driven entities like goldfingers', () => {
    const wrapper = mount(EntityDetailCard, {
      props: {
        item: {
          id: '1',
          name: 'Transmigrator',
          desc: 'Modern thinking still colors their view of cultivation',
          rarity: 'SR',
        } as any,
      },
      global: {
        plugins: [buildI18n()],
      },
    })

    const badge = wrapper.find('.grade-badge')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toBe('SR')
    expect(badge.classes()).toContain('grade-epic')
  })

  it('renders description from desc', () => {
    const wrapper = mount(EntityDetailCard, {
      props: {
        item: {
          id: '3',
          name: 'Child of Fortune',
          rarity: 'SSR',
          desc: 'You seem born under the favor of heaven and earth; opportunities others never find keep drifting your way.',
        } as any,
      },
      global: {
        plugins: [buildI18n()],
      },
    })

    expect(wrapper.text()).toContain('You seem born under the favor of heaven and earth')
  })

  it('renders legendary badge style for SSR entities', () => {
    const wrapper = mount(EntityDetailCard, {
      props: {
        item: {
          id: '2',
          name: 'Child of Fortune',
          desc: 'Favored by fate; opportunities come to you',
          rarity: 'SSR',
        } as any,
      },
      global: {
        plugins: [buildI18n()],
      },
    })

    const badge = wrapper.find('.grade-badge')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toBe('SSR')
    expect(badge.classes()).toContain('grade-legendary')
  })
})
