import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import SpeedControl from '@/components/game/SpeedControl.vue'
import game from '@/locales/en-US/game.json'

function createSpeedI18n() {
  return createI18n({
    legacy: false,
    locale: 'en-US',
    messages: { 'en-US': { game } },
  })
}

function mountControl(props: { speed: number; options: number[] }) {
  return mount(SpeedControl, {
    props,
    global: { plugins: [createSpeedI18n()] },
  })
}

describe('SpeedControl', () => {
  it('renders one button per allowed speed and marks the active one', () => {
    const wrapper = mountControl({ speed: 2, options: [0.5, 1, 2, 4] })

    const buttons = wrapper.findAll('button.speed-option')
    expect(buttons.map((button) => button.text())).toEqual(['0.5x', '1x', '2x', '4x'])

    const active = wrapper.findAll('button.speed-option--active')
    expect(active).toHaveLength(1)
    expect(active[0].text()).toBe('2x')
    expect(active[0].attributes('aria-pressed')).toBe('true')
    expect(buttons[0].attributes('aria-pressed')).toBe('false')
    expect(wrapper.find('.speed-control').attributes('aria-label')).toBe('Simulation speed')
    expect(buttons[3].attributes('title')).toBe('Set simulation speed to 4x')
  })

  it('emits select with the clicked speed', async () => {
    const wrapper = mountControl({ speed: 1, options: [0.5, 1, 2, 4] })

    await wrapper.find('button[data-speed="4"]').trigger('click')
    await wrapper.find('button[data-speed="0.5"]').trigger('click')

    expect(wrapper.emitted('select')).toEqual([[4], [0.5]])
  })

  it('does not emit when the active speed is clicked again', async () => {
    const wrapper = mountControl({ speed: 1, options: [0.5, 1, 2, 4] })

    await wrapper.find('button[data-speed="1"]').trigger('click')

    expect(wrapper.emitted('select')).toBeUndefined()
  })

  it('updates the active marker when the speed prop changes', async () => {
    const wrapper = mountControl({ speed: 1, options: [0.5, 1, 2, 4] })

    await wrapper.setProps({ speed: 0.5 })

    expect(wrapper.find('button.speed-option--active').text()).toBe('0.5x')
  })

  it('renders nothing until speed options are known', () => {
    const wrapper = mountControl({ speed: 1, options: [] })

    expect(wrapper.find('.speed-control').exists()).toBe(false)
  })
})
