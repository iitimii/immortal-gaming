import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, nextTick } from 'vue'

const mocks = vi.hoisted(() => ({
  fetchAvatarList: vi.fn(),
  fetchAvatarComparison: vi.fn(),
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

vi.mock('@/api/modules/avatar', () => ({
  avatarApi: {
    fetchAvatarList: mocks.fetchAvatarList,
    fetchAvatarComparison: mocks.fetchAvatarComparison,
  },
}))

vi.mock('@/stores/ui', () => ({
  useUiStore: () => ({ select: mocks.select }),
}))

import { normalizeAvatarComparison } from '@/api/mappers/avatarCompare'
import AvatarCompareModal from '@/components/game/panels/info/avatar-detail/AvatarCompareModal.vue'
import { makeCompareDTO } from '../../../../../fixtures/avatarCompare'

const avatarList = [
  { id: 'a1', name: 'Elder Lan', sect_name: 'Azure Cloud Sect', realm: 'CORE_FORMATION', cultivation_display: 'Core Formation', gender: 'male', age: 120 },
  { id: 'b1', name: 'Wanderer Qiu', sect_name: 'Rogue Cultivator', realm: 'QI_REFINEMENT', cultivation_display: 'Qi Refinement', gender: 'male', age: 40 },
  { id: 'c1', name: 'Mei Ling', sect_name: 'Azure Cloud Sect', realm: 'FOUNDATION_ESTABLISHMENT', cultivation_display: 'Foundation Establishment', gender: 'female', age: 60 },
]

// Global fake timers (see setup.ts) stall flushPromises; drain microtasks directly.
async function settle() {
  for (let i = 0; i < 5; i += 1) {
    await Promise.resolve()
  }
  await nextTick()
}

function mountModal() {
  return mount(AvatarCompareModal, {
    props: { show: true, avatarId: 'a1', avatarName: 'Elder Lan' },
  })
}

describe('AvatarCompareModal', () => {
  beforeEach(() => {
    mocks.fetchAvatarList.mockReset()
    mocks.fetchAvatarComparison.mockReset()
    mocks.select.mockReset()
  })

  it('shows a searchable picker of other avatars on initial mount', async () => {
    mocks.fetchAvatarList.mockResolvedValue(avatarList)
    const wrapper = mountModal()
    expect(mocks.fetchAvatarList).toHaveBeenCalledTimes(1)
    await settle()

    const candidates = wrapper.findAll('.candidate')
    expect(candidates.map((node) => node.attributes('data-avatar-id'))).toEqual(['b1', 'c1'])

    await wrapper.find('.search-input').setValue('mei')
    expect(wrapper.findAll('.candidate').map((node) => node.attributes('data-avatar-id'))).toEqual(['c1'])

    await wrapper.find('.search-input').setValue('nobody')
    expect(wrapper.findAll('.candidate')).toHaveLength(0)
    expect(wrapper.text()).toContain('game.info_panel.avatar.compare.no_candidates')
  })

  it('renders the side-by-side comparison with highlights and the win bar', async () => {
    mocks.fetchAvatarList.mockResolvedValue(avatarList)
    mocks.fetchAvatarComparison.mockResolvedValue(normalizeAvatarComparison(makeCompareDTO()))
    const wrapper = mountModal()
    await settle()

    await wrapper.find('[data-avatar-id="b1"]').trigger('click')
    await settle()

    expect(mocks.fetchAvatarComparison).toHaveBeenCalledWith('a1', 'b1')
    expect(wrapper.find('.side-a').text()).toBe('Elder Lan')
    expect(wrapper.find('.side-b').text()).toBe('Wanderer Qiu')

    const realmRow = wrapper.find('[data-row="realm"]')
    expect(realmRow.find('.cell-a').classes()).toContain('better')
    expect(realmRow.find('.cell-b').classes()).not.toContain('better')
    const stonesRow = wrapper.find('[data-row="spirit_stones"]')
    expect(stonesRow.find('.cell-b').classes()).toContain('better')
    expect(stonesRow.find('.cell-a').classes()).not.toContain('better')
    const lifespanRow = wrapper.find('[data-row="lifespan"]')
    expect(lifespanRow.findAll('.better')).toHaveLength(0)

    expect(wrapper.find('.win-fill-a').attributes('style')).toContain('width: 97.7%')
    expect(wrapper.find('.win-fill-b').attributes('style')).toContain('width: 2.3%')
    expect(wrapper.find('.win-value[data-side="a"]').classes()).toContain('favored')

    expect(wrapper.find('[data-relation="a_to_b"]').text()).toContain('Sworn Brother / Friend')
    expect(wrapper.find('[data-relation="b_to_a"]').text()).toContain('Stranger')
  })

  it('goes back to the picker and opens avatars by name', async () => {
    mocks.fetchAvatarList.mockResolvedValue(avatarList)
    mocks.fetchAvatarComparison.mockResolvedValue(normalizeAvatarComparison(makeCompareDTO()))
    const wrapper = mountModal()
    await settle()
    await wrapper.find('[data-avatar-id="b1"]').trigger('click')
    await settle()

    await wrapper.find('.side-b').trigger('click')
    expect(mocks.select).toHaveBeenCalledWith('avatar', 'b1')
    expect(wrapper.emitted('update:show')?.[0]).toEqual([false])

    await wrapper.find('.back-btn').trigger('click')
    expect(wrapper.findAll('.candidate')).toHaveLength(2)
  })

  it('shows the error message when the comparison request fails', async () => {
    mocks.fetchAvatarList.mockResolvedValue(avatarList)
    mocks.fetchAvatarComparison.mockRejectedValue(new Error('Avatar not found'))
    const wrapper = mountModal()
    await settle()

    await wrapper.find('[data-avatar-id="c1"]').trigger('click')
    await settle()

    expect(wrapper.find('.compare-error').text()).toBe('Avatar not found')
    expect(wrapper.find('.compare-table').exists()).toBe(false)
  })
})
