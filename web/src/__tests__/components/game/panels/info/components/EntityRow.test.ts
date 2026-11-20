import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'
import EntityRow from '@/components/game/panels/info/components/EntityRow.vue'

function buildI18n() {
  return createI18n({
    legacy: false,
    locale: 'en-US',
    messages: {
      'en-US': {
        technique_grades: {
          MIDDLE: 'Mid Grade',
        },
      },
    },
  })
}

describe('EntityRow', () => {
  const baseItem = {
    name: 'Golden Light Shield',
    grade: 'MIDDLE',
  }

  it('renders grade and meta on a stacked details line', () => {
    const wrapper = mount(EntityRow, {
      props: {
        item: baseItem as any,
        meta: 'Proficiency 0.0%',
        detailsBelow: true,
      },
      global: {
        plugins: [buildI18n()],
        directives: {
          sound: () => {},
        },
      },
    })

    expect(wrapper.classes()).toContain('details-below')
    expect(wrapper.find('.details-line').exists()).toBe(true)
    expect(wrapper.find('.grade').text()).toBe('Mid Grade')
    expect(wrapper.find('.meta').text()).toBe('Proficiency 0.0%')
  })
})
