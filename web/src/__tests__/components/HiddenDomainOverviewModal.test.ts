import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { h, defineComponent } from 'vue'

let mockActiveDomains: any[] = []

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock('@/stores/world', () => ({
  useWorldStore: () => ({
    get activeDomains() {
      return mockActiveDomains
    },
  }),
}))

vi.mock('naive-ui', () => ({
  NModal: defineComponent({
    name: 'NModal',
    props: ['show', 'preset', 'title'],
    emits: ['update:show'],
    setup(props, { slots }) {
      return () => props.show ? h('div', { class: 'n-modal-stub' }, slots.default?.()) : null
    },
  }),
  NEmpty: defineComponent({
    name: 'NEmpty',
    props: ['description'],
    setup(props) {
      return () => h('div', { class: 'n-empty-stub' }, props.description)
    },
  }),
  NTag: defineComponent({
    name: 'NTag',
    setup(_, { slots }) {
      return () => h('span', { class: 'n-tag-stub' }, slots.default?.())
    },
  }),
}))

import HiddenDomainOverviewModal from '@/components/game/panels/HiddenDomainOverviewModal.vue'

describe('HiddenDomainOverviewModal', () => {
  it('renders hidden domain cards without open or closed status text', () => {
    mockActiveDomains = [
      {
        id: '1',
        name: 'Purple Bamboo Hidden Domain',
        desc: 'Suited to trials for mid-level cultivators.',
        required_realm: 'CORE_FORMATION',
        danger_prob: 0.3,
        drop_prob: 0.5,
        cd_years: 5,
        open_prob: 0.2,
      },
    ]

    const wrapper = mount(HiddenDomainOverviewModal, {
      props: { show: true },
    })

    expect(wrapper.find('.domain-card').exists()).toBe(true)
    expect(wrapper.text()).toContain('Purple Bamboo Hidden Domain')
    expect(wrapper.text()).toContain('game.status_bar.hidden_domain.required_realm')
  })

  it('renders empty state when there are no hidden domains', () => {
    mockActiveDomains = []

    const wrapper = mount(HiddenDomainOverviewModal, {
      props: { show: true },
    })

    expect(wrapper.find('.n-empty-stub').exists()).toBe(true)
    expect(wrapper.text()).toContain('game.status_bar.hidden_domain.empty')
  })
})
