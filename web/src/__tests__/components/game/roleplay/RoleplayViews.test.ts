import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'

import RoleplayChoiceView from '@/components/game/roleplay/RoleplayChoiceView.vue'
import RoleplayConversationView from '@/components/game/roleplay/RoleplayConversationView.vue'
import RoleplayDecisionView from '@/components/game/roleplay/RoleplayDecisionView.vue'
import RoleplayDockHeader from '@/components/game/roleplay/RoleplayDockHeader.vue'
import RoleplayIdleView from '@/components/game/roleplay/RoleplayIdleView.vue'
import RoleplayInteractionHistory from '@/components/game/roleplay/RoleplayInteractionHistory.vue'
import RoleplaySectionHeader from '@/components/game/roleplay/RoleplaySectionHeader.vue'

function createRoleplayI18n() {
  return createI18n({
    legacy: false,
    locale: 'en-US',
    messages: {
      'en-US': {
        game: {
          roleplay: {
            panel: { stop: 'Stop Roleplay' },
            dock: {
              collapse: 'Collapse roleplay panel',
              expand: 'Expand roleplay panel',
              collapse_short: 'Min',
              expand_short: 'Max',
            },
            conversation: {
              end: 'End Conversation',
              end_disabled: 'You cannot end the conversation while waiting for a reply',
              placeholder: 'Enter what you want to say.',
            },
            decision: {
              placeholder: "Enter the character's next intent, for example: recover first, then explore nearby.",
            },
            idle: {
              hint: "You are still observing the world in omniscient view. When this character's action chain finishes, the next prompt will wait for you here.",
            },
          },
        },
      },
    },
  })
}

describe('Roleplay subviews', () => {
  it('renders dock header and emits exit', async () => {
    const wrapper = mount(RoleplayDockHeader, {
      global: { plugins: [createRoleplayI18n()] },
      props: {
        avatarName: 'Wenren Wu',
        statusText: 'Awaiting Command',
        requestSummary: 'Needs a next action',
        isSubmitting: false,
        isCollapsed: false,
      },
    })

    expect(wrapper.text()).toContain('Wenren Wu')
    expect(wrapper.text()).toContain('Awaiting Command')
    expect(wrapper.text()).toContain('Needs a next action')

    await wrapper.find('button.roleplay-dock__exit').trigger('click')
    expect(wrapper.emitted('exit')).toHaveLength(1)
    await wrapper.find('button.roleplay-dock__collapse').trigger('click')
    expect(wrapper.emitted('toggle-collapse')).toHaveLength(1)
  })

  it('renders section header copy', () => {
    const wrapper = mount(RoleplaySectionHeader, {
      props: {
        title: 'Decision',
        caption: 'Enter one intent and the system will expand it into an action chain',
      },
    })

    expect(wrapper.text()).toContain('Decision')
    expect(wrapper.text()).toContain('Enter one intent and the system will expand it into an action chain')
  })

  it('updates and submits decision input', async () => {
    const wrapper = mount(RoleplayDecisionView, {
      global: { plugins: [createRoleplayI18n()] },
      props: {
        description: 'Enter one intent.',
        modelValue: '',
        errorText: '',
        isSubmitting: false,
        submitText: 'Submit Command',
      },
    })

    const textarea = wrapper.find('textarea.roleplay-dock__input')
    await textarea.setValue('Restore spiritual qi first.')

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['Restore spiritual qi first.'])

    await wrapper.setProps({ modelValue: 'Restore spiritual qi first.' })
    await wrapper.find('button.roleplay-dock__submit').trigger('click')

    expect(wrapper.emitted('submit')).toHaveLength(1)

    await textarea.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('submit')).toHaveLength(2)

    await textarea.trigger('keydown', { key: 'Enter', shiftKey: true })
    expect(wrapper.emitted('submit')).toHaveLength(2)
  })

  it('renders choices and emits selected key', async () => {
    const wrapper = mount(RoleplayChoiceView, {
      props: {
        description: 'Choose one response.',
        options: [
          { key: 'accept', title: 'Accept', description: 'Go to the meeting', variant: 'accept' },
          { key: 'reject', title: 'Decline', description: 'Politely decline the invitation', variant: 'reject' },
        ],
        errorText: '',
        isSubmitting: false,
        submittingText: '',
      },
    })

    const buttons = wrapper.findAll('button.roleplay-dock__choice')
    expect(buttons).toHaveLength(2)
    expect(buttons[0].classes()).toContain('roleplay-dock__choice--accept')
    expect(buttons[1].classes()).toContain('roleplay-dock__choice--reject')

    await buttons[1].trigger('click')
    expect(wrapper.emitted('submit')?.[0]).toEqual(['reject'])

    await wrapper.find('.roleplay-dock__choice-list').trigger('keydown', { key: '1' })
    expect(wrapper.emitted('submit')?.[1]).toEqual(['accept'])
  })

  it('renders conversation view and emits send/end', async () => {
    const wrapper = mount(RoleplayConversationView, {
      global: { plugins: [createRoleplayI18n()] },
      props: {
        avatarName: 'Wenren Wu',
        targetName: 'Yin Changsheng',
        description: 'The world is paused, waiting for you to continue speaking.',
        caption: 'The player speaks as Wenren Wu, and the other side replies through the LLM',
        modelValue: '',
        messages: [
          {
            id: 'm1',
            role: 'assistant',
            speaker_name: 'Yin Changsheng',
            content: 'Why have you come?',
            created_at: 1,
          },
        ],
        errorText: '',
        isSubmitting: false,
        submitText: 'Send',
      },
    })

    expect(wrapper.text()).toContain('Wenren Wu ↔ Yin Changsheng')
    expect(wrapper.text()).toContain('Why have you come?')

    const textarea = wrapper.find('textarea.roleplay-dock__input--conversation')
    await textarea.setValue('I have come seeking a path.')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['I have come seeking a path.'])

    await wrapper.setProps({ modelValue: 'I have come seeking a path.' })
    await wrapper.find('.roleplay-dock__conversation-actions .roleplay-dock__submit').trigger('click')
    expect(wrapper.emitted('send')).toHaveLength(1)

    await textarea.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('send')).toHaveLength(2)

    await textarea.trigger('keydown', { key: 'Enter', shiftKey: true })
    expect(wrapper.emitted('send')).toHaveLength(2)

    await wrapper.find('button.roleplay-dock__submit--quiet').trigger('click')
    expect(wrapper.emitted('end')).toHaveLength(1)
  })

  it('renders idle hint', () => {
    const wrapper = mount(RoleplayIdleView, {
      global: { plugins: [createRoleplayI18n()] },
    })
    expect(wrapper.text()).toContain('You are still observing the world in omniscient view')
  })

  it('limits interaction history to recent items', () => {
    const wrapper = mount(RoleplayInteractionHistory, {
      props: {
        maxItems: 2,
        playerName: 'Wenren Wu',
        counterpartName: 'Yin Changsheng',
        items: [
          { type: 'conversation_player', created_at: 1, text: 'First entry' },
          { type: 'conversation_assistant', created_at: 2, text: 'Second entry' },
          { type: 'command', created_at: 3, text: 'Third entry' },
        ],
      },
    })

    expect(wrapper.text()).not.toContain('First entry')
    expect(wrapper.text()).toContain('Second entry')
    expect(wrapper.text()).toContain('Third entry')
    expect(wrapper.text()).toContain('Yin Changsheng')
  })
})
