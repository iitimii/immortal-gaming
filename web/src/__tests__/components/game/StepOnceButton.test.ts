import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import StepOnceButton from '@/components/game/StepOnceButton.vue'
import game from '@/locales/en-US/game.json'

function mountButton(props: { enabled: boolean; busy: boolean }) {
  return mount(StepOnceButton, {
    props,
    global: {
      plugins: [
        createI18n({
          legacy: false,
          locale: 'en-US',
          messages: { 'en-US': { game } },
        }),
      ],
    },
  })
}

describe('StepOnceButton', () => {
  it('emits step when enabled and clicked', async () => {
    const wrapper = mountButton({ enabled: true, busy: false })
    const button = wrapper.find('button.step-once-btn')

    expect(button.attributes('disabled')).toBeUndefined()
    expect(button.attributes('aria-label')).toBe('Step one month')
    expect(button.attributes('title')).toBe('Step one month')

    await button.trigger('click')

    expect(wrapper.emitted('step')).toHaveLength(1)
  })

  it('is disabled with an explanatory title when stepping is unavailable', async () => {
    const wrapper = mountButton({ enabled: false, busy: false })
    const button = wrapper.find('button.step-once-btn')

    expect(button.attributes('disabled')).toBeDefined()
    expect(button.attributes('title')).toBe('Pause the game to step one month at a time')

    await button.trigger('click')

    expect(wrapper.emitted('step')).toBeUndefined()
  })

  it('shows the busy state while a step is in flight', async () => {
    const wrapper = mountButton({ enabled: false, busy: true })
    const button = wrapper.find('button.step-once-btn')

    expect(button.attributes('disabled')).toBeDefined()
    expect(button.attributes('aria-busy')).toBe('true')
    expect(button.classes()).toContain('step-once-btn--busy')
    expect(button.attributes('title')).toBe('Advancing one month...')

    await button.trigger('click')
    expect(wrapper.emitted('step')).toBeUndefined()
  })

  it('re-enables after the busy state clears', async () => {
    const wrapper = mountButton({ enabled: false, busy: true })

    await wrapper.setProps({ enabled: true, busy: false })

    const button = wrapper.find('button.step-once-btn')
    expect(button.attributes('disabled')).toBeUndefined()
    expect(button.attributes('aria-busy')).toBe('false')
  })
})
