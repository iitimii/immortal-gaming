import { mount } from '@vue/test-utils'
import { reactive, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'

import RoleplayDock from '@/components/game/RoleplayDock.vue'

const { eventApiMock } = vi.hoisted(() => ({
  eventApiMock: {
    fetchEvents: vi.fn(async () => ({ events: [] })),
  },
}))

const roleplayStoreMock = reactive({
  session: {
    controlled_avatar_id: null as string | null,
    status: 'inactive',
    pending_request: null as null | {
      request_id: string
      type: string
      avatar_id: string
      title: string
      description: string
      options?: Array<{ key: string; title: string; description: string; variant?: 'accept' | 'reject' | 'default' }>
      messages?: Array<{ id: string; role: string; speaker_name: string; content: string; created_at: number }>
    },
    last_prompt_context: null as Record<string, unknown> | null,
    conversation_session: null as null | {
      messages: Array<{ id: string; role: string; speaker_name: string; content: string; created_at: number }>
    },
    interaction_history: [] as Array<Record<string, unknown>>,
  },
  isSubmitting: false,
  error: null as string | null,
  fetchSession: vi.fn(async () => roleplayStoreMock.session),
  submitDecision: vi.fn(async () => ({ status: 'ok' })),
  submitChoice: vi.fn(async () => ({ status: 'ok' })),
  sendConversation: vi.fn(async () => ({ status: 'ok' })),
  endConversation: vi.fn(async () => ({ status: 'ok' })),
  stopRoleplay: vi.fn(async () => ({
    controlled_avatar_id: null,
    status: 'inactive',
    pending_request: null,
    last_prompt_context: null,
  })),
})

vi.mock('@/stores/roleplay', () => ({
  useRoleplayStore: () => roleplayStoreMock,
}))

vi.mock('@/api', () => ({
  eventApi: eventApiMock,
}))

vi.mock('@/api/mappers/event', () => ({
  mapEventDtosToTimeline: vi.fn((events: unknown[]) => events),
}))

vi.mock('@/utils/appError', () => ({
  logError: vi.fn(),
}))

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
              interaction_title: 'Interaction Log',
              interaction_caption: 'Input and output during this roleplay session',
              interaction_empty: 'There are no new interaction records yet.',
              collapse: 'Collapse roleplay panel',
              expand: 'Expand roleplay panel',
              collapse_short: 'Min',
              expand_short: 'Max',
            },
            status: {
              awaiting_decision: 'Awaiting Command',
              awaiting_choice: 'Awaiting Choice',
              conversing: 'Conversing',
              submitting: 'Submitting',
              observing: 'Observing',
            },
            summary: {
              decision: 'Needs a next action',
              choice: 'Needs a response',
              conversation: 'Talking with {target}',
              observing: 'Current action chain is still running',
            },
            request: {
              title_decision: 'Decision',
              title_choice: 'Choice',
              title_conversation: 'Conversation',
              title_observing: 'Observe',
              caption_decision: 'Enter one intent and the system will expand it into an action chain',
              caption_choice: 'Make one response from limited options',
              caption_conversation: 'The player speaks as {avatar}, and the other side replies through the LLM',
              caption_observing: 'There is no request that needs immediate handling right now',
              decision_default_description: "Enter one intent and the system will expand it into this character's next action chain.",
              choice_default_description: 'Choose one response.',
              conversation_default_description: 'The world is paused, waiting for you to continue speaking as the current character.',
            },
            decision: {
              placeholder: "Enter the character's next intent, for example: recover first, then explore nearby.",
              submit: 'Submit Command',
              submitting: 'Processing...',
            },
            choice: {
              submitting: 'Processing your choice, please wait...',
            },
            conversation: {
              placeholder: 'Enter what you want to say.',
              submit: 'Send',
              sending: 'Sending...',
              awaiting_reply: 'Waiting for reply...',
              end: 'End Conversation',
              end_disabled: 'You cannot end the conversation while waiting for a reply',
            },
            feedback: {
              decision_submitted: 'Command submitted: {text}',
              choice_submitted: 'Choice submitted: {text}',
              conversation_failed: 'Send failed. Your text was kept so you can edit and retry.',
            },
            idle: {
              hint: "You are still observing the world in omniscient view. When this character's action chain finishes, the next prompt will wait for you here.",
            },
            fallback: {
              avatar_name: 'Avatar',
              counterpart_name: 'Other Side',
            },
          },
        },
      },
    },
  })
}

describe('RoleplayDock', () => {
  beforeEach(() => {
    roleplayStoreMock.session.controlled_avatar_id = null
    roleplayStoreMock.session.status = 'inactive'
    roleplayStoreMock.session.pending_request = null
    roleplayStoreMock.session.last_prompt_context = null
    roleplayStoreMock.session.conversation_session = null
    roleplayStoreMock.session.interaction_history = []
    roleplayStoreMock.isSubmitting = false
    roleplayStoreMock.error = null
    roleplayStoreMock.fetchSession.mockClear()
    roleplayStoreMock.submitDecision.mockClear()
    roleplayStoreMock.submitChoice.mockClear()
    roleplayStoreMock.sendConversation.mockClear()
    roleplayStoreMock.endConversation.mockClear()
    roleplayStoreMock.stopRoleplay.mockClear()
    eventApiMock.fetchEvents.mockClear()
    eventApiMock.fetchEvents.mockResolvedValue({ events: [] })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders decision console and submits command text', async () => {
    roleplayStoreMock.session.controlled_avatar_id = 'avatar-1'
    roleplayStoreMock.session.status = 'awaiting_decision'
    roleplayStoreMock.session.pending_request = {
      request_id: 'req-1',
      type: 'decision',
      avatar_id: 'avatar-1',
      title: 'Wenren Wu needs a new command',
      description: 'The world is paused, waiting for your roleplay command.',
    }
    roleplayStoreMock.session.last_prompt_context = {
      avatar_name: 'Wenren Wu',
    }
    roleplayStoreMock.session.interaction_history = [
      { type: 'command', created_at: 1, text: 'Recover first, then explore.' },
      {
        type: 'action_chain',
        created_at: 2,
        actions: [{ action_name: 'MoveToRegion', tokens: [{ kind: 'verb', text: 'Move to' }, { kind: 'arg', text: 'Bluestone Valley' }] }],
      },
    ]

    const wrapper = mount(RoleplayDock, { global: { plugins: [createRoleplayI18n()] } })
    await nextTick()

    expect(wrapper.text()).toContain('Wenren Wu')
    expect(wrapper.text()).toContain('Awaiting Command')
    expect(wrapper.text()).toContain('Bluestone Valley')

    const textarea = wrapper.find('textarea.roleplay-dock__input')
    expect(textarea.exists()).toBe(true)
    await textarea.setValue('Recover first, then explore.')
    await wrapper.find('button.roleplay-dock__submit').trigger('click')
    await nextTick()

    expect(wrapper.text()).toContain('Command submitted: Recover first, then explore.')

    expect(roleplayStoreMock.submitDecision).toHaveBeenCalledWith({
      avatar_id: 'avatar-1',
      request_id: 'req-1',
      command_text: 'Recover first, then explore.',
    })
  })

  it('renders choice buttons and submits selected option', async () => {
    roleplayStoreMock.session.controlled_avatar_id = 'avatar-1'
    roleplayStoreMock.session.status = 'awaiting_choice'
    roleplayStoreMock.session.pending_request = {
      request_id: 'req-choice',
      type: 'choice',
      avatar_id: 'avatar-1',
      title: 'Accept the invitation?',
      description: 'The other side is waiting for your response.',
      options: [
        { key: 'accept', title: 'Accept', description: 'Go to the meeting', variant: 'accept' },
        { key: 'reject', title: 'Decline', description: 'Politely decline the invitation', variant: 'reject' },
      ],
    }
    roleplayStoreMock.session.last_prompt_context = {
      avatar_name: 'Wenren Wu',
    }
    roleplayStoreMock.session.interaction_history = [
      { type: 'choice_prompt', created_at: 1, text: 'Leng Qingya invites you to join Haoran Academy as a disciple.' },
      { type: 'choice', created_at: 1, text: 'Decline: Politely decline the invitation' },
    ]

    const wrapper = mount(RoleplayDock, { global: { plugins: [createRoleplayI18n()] } })
    await nextTick()

    expect(wrapper.text()).toContain('Leng Qingya invites you to join Haoran Academy as a disciple.')
    expect(wrapper.text()).toContain('Decline: Politely decline the invitation')
    const buttons = wrapper.findAll('button.roleplay-dock__choice')
    expect(buttons).toHaveLength(2)
    await buttons[1].trigger('click')
    await nextTick()

    expect(wrapper.text()).toContain('Choice submitted: Decline')

    expect(roleplayStoreMock.submitChoice).toHaveBeenCalledWith({
      avatar_id: 'avatar-1',
      request_id: 'req-choice',
      selected_key: 'reject',
    })
  })

  it('supports resize drag on the dock handle', async () => {
    roleplayStoreMock.session.controlled_avatar_id = 'avatar-1'
    roleplayStoreMock.session.status = 'observing'
    roleplayStoreMock.session.last_prompt_context = {
      avatar_name: 'Wenren Wu',
    }

    const wrapper = mount(RoleplayDock, {
      attachTo: document.body,
      global: { plugins: [createRoleplayI18n()] },
    })
    await nextTick()

    expect((wrapper.element as HTMLElement).style.height).toBe('214px')

    await wrapper.find('.roleplay-dock__resize-handle').trigger('mousedown', {
      clientY: 300,
      preventDefault: () => {},
    })
    document.dispatchEvent(new MouseEvent('mousemove', { clientY: 250 }))
    await nextTick()

    expect((wrapper.element as HTMLElement).style.height).toBe('264px')

    document.dispatchEvent(new MouseEvent('mouseup'))
    await nextTick()

    wrapper.unmount()
  })

  it('keeps interaction history visible while observing', async () => {
    roleplayStoreMock.session.controlled_avatar_id = 'avatar-1'
    roleplayStoreMock.session.status = 'observing'
    roleplayStoreMock.session.last_prompt_context = {
      avatar_name: 'Wenren Wu',
    }
    roleplayStoreMock.session.interaction_history = [
      { type: 'command', created_at: 1, text: 'Recover first, then explore.' },
      {
        type: 'action_chain',
        created_at: 2,
        actions: [{ action_name: 'MoveToRegion', tokens: [{ kind: 'verb', text: 'Move to' }, { kind: 'arg', text: 'Bluestone Valley' }] }],
      },
    ]

    const wrapper = mount(RoleplayDock, { global: { plugins: [createRoleplayI18n()] } })
    await nextTick()

    expect(wrapper.text()).toContain('You are still observing the world in omniscient view')
    expect(wrapper.text()).toContain('Recover first, then explore.')
    expect(wrapper.text()).toContain('Move to')
    expect(wrapper.text()).toContain('Bluestone Valley')
  })

  it('renders conversation mode and sends chat messages', async () => {
    roleplayStoreMock.session.controlled_avatar_id = 'avatar-1'
    roleplayStoreMock.session.status = 'conversing'
    roleplayStoreMock.session.pending_request = {
      request_id: 'req-conversation',
      type: 'conversation',
      avatar_id: 'avatar-1',
      target_avatar_id: 'avatar-2',
      title: 'Wenren Wu is talking with Yin Changsheng',
      description: 'The world is paused, waiting for you to continue speaking.',
      messages: [
        { id: 'm1', role: 'assistant', speaker_name: 'Yin Changsheng', content: 'Why have you come?', created_at: 1 },
      ],
    }
    roleplayStoreMock.session.conversation_session = {
      messages: [
        { id: 'm1', role: 'assistant', speaker_name: 'Yin Changsheng', content: 'Why have you come?', created_at: 1 },
      ],
    }
    roleplayStoreMock.session.last_prompt_context = {
      avatar_name: 'Wenren Wu',
      target_avatar_name: 'Yin Changsheng',
    }
    roleplayStoreMock.session.interaction_history = [
      { type: 'conversation_player', created_at: 1, text: 'I have come seeking a path.' },
      { type: 'conversation_assistant', created_at: 2, text: 'Why have you come?' },
    ]

    const wrapper = mount(RoleplayDock, { global: { plugins: [createRoleplayI18n()] } })
    await nextTick()

    expect(wrapper.text()).toContain('Wenren Wu ↔ Yin Changsheng')
    expect(wrapper.text()).toContain('Why have you come?')
    expect(wrapper.text()).toContain('I have come seeking a path.')

    const textarea = wrapper.find('.roleplay-dock__input--conversation')
    await textarea.setValue('I have come seeking a path.')
    await wrapper.find('.roleplay-dock__conversation-actions .roleplay-dock__submit').trigger('click')

    expect(roleplayStoreMock.sendConversation).toHaveBeenCalledWith({
      avatar_id: 'avatar-1',
      request_id: 'req-conversation',
      message: 'I have come seeking a path.',
    })
  })

  it('shows optimistic player message while waiting for conversation reply', async () => {
    let resolveSend: (() => void) | null = null
    roleplayStoreMock.sendConversation.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveSend = () => resolve({ status: 'ok' })
        })
    )

    roleplayStoreMock.session.controlled_avatar_id = 'avatar-1'
    roleplayStoreMock.session.status = 'conversing'
    roleplayStoreMock.session.pending_request = {
      request_id: 'req-conversation',
      type: 'conversation',
      avatar_id: 'avatar-1',
      target_avatar_id: 'avatar-2',
      title: 'Wenren Wu is talking with Yin Changsheng',
      description: 'The world is paused, waiting for you to continue speaking.',
      messages: [],
    }
    roleplayStoreMock.session.conversation_session = {
      messages: [],
    }
    roleplayStoreMock.session.last_prompt_context = {
      avatar_name: 'Wenren Wu',
      target_avatar_name: 'Yin Changsheng',
    }

    const wrapper = mount(RoleplayDock, { global: { plugins: [createRoleplayI18n()] } })
    await nextTick()

    const textarea = wrapper.find('.roleplay-dock__input--conversation')
    await textarea.setValue('Hello')
    await wrapper.find('.roleplay-dock__conversation-actions .roleplay-dock__submit').trigger('click')
    await nextTick()

    expect(wrapper.text()).toContain('Hello')
    expect(wrapper.text()).toContain('Waiting for reply...')

    resolveSend?.()
    await nextTick()
    await nextTick()
  })

  it('does not keep polling roleplay session when no active roleplay exists', async () => {
    vi.useFakeTimers()

    const wrapper = mount(RoleplayDock, { global: { plugins: [createRoleplayI18n()] } })
    await nextTick()

    expect(roleplayStoreMock.fetchSession).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(3000)

    expect(roleplayStoreMock.fetchSession).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('keeps polling roleplay session while an avatar is under roleplay control', async () => {
    vi.useFakeTimers()
    roleplayStoreMock.session.controlled_avatar_id = 'avatar-1'
    roleplayStoreMock.session.status = 'observing'
    roleplayStoreMock.session.last_prompt_context = {
      avatar_name: 'Wenren Wu',
    }

    const wrapper = mount(RoleplayDock, { global: { plugins: [createRoleplayI18n()] } })
    await nextTick()

    expect(roleplayStoreMock.fetchSession).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(2200)

    expect(roleplayStoreMock.fetchSession.mock.calls.length).toBeGreaterThanOrEqual(3)
    wrapper.unmount()
  })
})
