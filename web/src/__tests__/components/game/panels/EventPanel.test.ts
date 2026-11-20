import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import EventPanel from '@/components/game/panels/EventPanel.vue'
import { createI18n } from 'vue-i18n'
import { reactive } from 'vue'
import { NSelect } from 'naive-ui'

const avatarStoreMock = reactive({
  avatarList: [
    { id: 'a1', name: 'Alice', is_dead: false },
    { id: 'a2', name: 'Bob', is_dead: false },
  ],
})

const eventStoreMock = reactive({
  events: [],
  eventsHasMore: false,
  eventsLoading: false,
  resetEvents: vi.fn(async () => {}),
  loadMoreEvents: vi.fn(async () => {}),
})

const uiStoreMock = {
  select: vi.fn(),
}

const roleplayStoreMock = reactive({
  session: {
    controlled_avatar_id: null as string | null,
    status: 'inactive',
    pending_request: null,
    last_prompt_context: null as Record<string, unknown> | null,
  },
})

const mapStoreMock = reactive({
  regions: new Map<string | number, { id: string; name: string; type: string; sect_id?: number; sect_name?: string; sect_color?: string; x: number; y: number }>(),
  isLoaded: true,
})

const sectStoreMock = reactive({
  activeSectOptions: [
    { label: 'Qingyun Sect', value: 1 },
    { label: 'Heavenly Fire Sect', value: 2 },
  ],
  isLoaded: true,
  isLoading: false,
  refreshTerritories: vi.fn(async () => {}),
})

vi.mock('@/stores/avatar', () => ({
  useAvatarStore: () => avatarStoreMock,
}))

vi.mock('@/stores/event', () => ({
  useEventStore: () => eventStoreMock,
}))

vi.mock('@/stores/ui', () => ({
  useUiStore: () => uiStoreMock,
}))

vi.mock('@/stores/roleplay', () => ({
  useRoleplayStore: () => roleplayStoreMock,
}))

vi.mock('@/stores/map', () => ({
  useMapStore: () => mapStoreMock,
}))

vi.mock('@/stores/sect', () => ({
  useSectStore: () => sectStoreMock,
}))

function createEventPanelI18n(locale = 'en-US') {
  return createI18n({
    legacy: false,
    locale,
    messages: {
      'en-US': {
        game: {
          event_panel: {
            title: 'Events',
            filter_all: 'All',
            filter_all_sects: 'All Sects',
            filter_event_scope_all: 'All Events',
            filter_event_scope_major: 'Major',
            filter_event_scope_minor: 'Minor',
            deceased: '(dead)',
            load_more: 'load',
            roleplay_locked: 'locked: {avatar}',
            story_subject_prefix: '[{avatar}] {content}',
            empty_none: 'none',
            empty_single: 'none',
          },
          event_templates: {
            nickname_awarded: '{avatar_name} is now "{nickname}".',
          },
        },
        common: { loading: 'loading', year: 'Y', month: 'M' },
      },
    },
  })
}

describe('EventPanel', () => {
  beforeEach(() => {
    eventStoreMock.events = []
    eventStoreMock.eventsHasMore = false
    eventStoreMock.eventsLoading = false
    eventStoreMock.resetEvents.mockClear()
    eventStoreMock.loadMoreEvents.mockClear()
    uiStoreMock.select.mockClear()
    roleplayStoreMock.session.controlled_avatar_id = null
    roleplayStoreMock.session.status = 'inactive'
    roleplayStoreMock.session.last_prompt_context = null
    sectStoreMock.refreshTerritories.mockClear()
    sectStoreMock.activeSectOptions = [
      { label: 'Qingyun Sect', value: 1 },
      { label: 'Heavenly Fire Sect', value: 2 },
    ]
    sectStoreMock.isLoaded = true
    sectStoreMock.isLoading = false
    mapStoreMock.regions = new Map([
      ['r1', { id: 'r1', name: 'Mingxin Mountain', type: 'sect', sect_id: 1, sect_name: 'Qingyun Sect', sect_color: '#4DD0E1', x: 10, y: 10 }],
      ['r2', { id: 'r2', name: 'Crimson Flame Peak', type: 'sect', sect_id: 2, sect_name: 'Heavenly Fire Sect', sect_color: '#8D6E63', x: 20, y: 20 }],
    ])
  })

  it('should render successfully', () => {
    const i18n = createEventPanelI18n()

    const wrapper = mount(EventPanel, {
      global: {
        plugins: [i18n],
        directives: {
          sound: () => {}
        }
      }
    })

    expect(wrapper.exists()).toBe(true)
  })

  it('reloads the full default event page when mounted', async () => {
    const i18n = createEventPanelI18n()

    mount(EventPanel, {
      global: {
        plugins: [i18n],
      },
    })

    await Promise.resolve()

    expect(eventStoreMock.resetEvents).toHaveBeenCalledWith({})
  })

  it('replaces incomplete startup snapshot events with the full default event page on mount', async () => {
    const i18n = createEventPanelI18n()
    eventStoreMock.events = [
      {
        id: 'recent-only',
        text: '',
        content: 'Recent event from startup snapshot',
        year: 100,
        month: 1,
        timestamp: 1201,
        relatedAvatarIds: [],
        isMajor: false,
        isStory: false,
      },
    ]
    eventStoreMock.resetEvents.mockImplementationOnce(async () => {
      eventStoreMock.events = [
        {
          id: 'older-from-page',
          text: '',
          content: 'Older event from full event page',
          year: 100,
          month: 1,
          timestamp: 1200,
          relatedAvatarIds: [],
          isMajor: false,
          isStory: false,
        },
        {
          id: 'recent-only',
          text: '',
          content: 'Recent event from startup snapshot',
          year: 100,
          month: 1,
          timestamp: 1201,
          relatedAvatarIds: [],
          isMajor: false,
          isStory: false,
        },
      ]
    })

    const wrapper = mount(EventPanel, {
      global: {
        plugins: [i18n],
      },
    })

    expect(wrapper.text()).not.toContain('Older event from full event page')

    await Promise.resolve()
    await wrapper.vm.$nextTick()

    expect(eventStoreMock.resetEvents).toHaveBeenCalledWith({})
    expect(wrapper.text()).toContain('Older event from full event page')
    expect(wrapper.text()).toContain('Recent event from startup snapshot')
  })

  it('should render event content as text, not raw html', async () => {
    const i18n = createEventPanelI18n()

    eventStoreMock.events = [
      {
        id: 'e1',
        text: '',
        content: '<img src=x onerror=alert(1)> Alice',
        year: 1,
        month: 1,
        timestamp: 13,
        relatedAvatarIds: ['a1'],
        isMajor: false,
        isStory: false,
      },
    ]

    const wrapper = mount(EventPanel, {
      global: {
        plugins: [i18n],
      },
    })

    const html = wrapper.html()
    expect(html).not.toContain('<img')
    expect(html).toContain('&lt;img src=x onerror=alert(1)&gt;')
    expect(wrapper.find('.clickable-avatar').text()).toBe('Alice')
  })

  it('should render clickable sect name with fixed color and jump to sect panel', async () => {
    const i18n = createEventPanelI18n()

    eventStoreMock.events = [
      {
        id: 'e2',
        text: '',
        content: 'Alice joined Qingyun Sect',
        year: 1,
        month: 2,
        timestamp: 14,
        relatedAvatarIds: ['a1'],
        relatedSects: [1],
        isMajor: false,
        isStory: false,
      },
    ]

    const wrapper = mount(EventPanel, {
      global: { plugins: [i18n] },
    })

    const sectNode = wrapper.find('.clickable-sect')
    expect(sectNode.exists()).toBe(true)
    expect(sectNode.text()).toBe('Qingyun Sect')
    expect(sectNode.attributes('style')).toContain('rgb(77, 208, 225)')

    await sectNode.trigger('click')
    expect(uiStoreMock.select).toHaveBeenCalledWith('sect', '1')
  })

  it('should render structured event text from locale template', () => {
    const i18n = createEventPanelI18n()

    eventStoreMock.events = [
      {
        id: 'e3',
        text: '',
        content: 'Old fallback content',
        year: 105,
        month: 12,
        timestamp: 1272,
        relatedAvatarIds: ['a1'],
        isMajor: true,
        isStory: false,
        renderKey: 'nickname_awarded',
        renderParams: {
          avatar_name: 'Alice',
          nickname: 'Lord of the Crimson Blood Holy Land',
        },
      },
    ]

    const wrapper = mount(EventPanel, {
      global: { plugins: [i18n] },
    })

    expect(wrapper.text()).toContain('Alice is now "Lord of the Crimson Blood Holy Land".')
    expect(wrapper.text()).not.toContain('Old fallback content')
  })

  it('renders subject tag when event text omits the avatar name', () => {
    const i18n = createEventPanelI18n()

    eventStoreMock.events = [
      {
        id: 'story-missing-name',
        text: '',
        content: 'He sat through the night and found a trace of insight.',
        year: 1,
        month: 3,
        timestamp: 15,
        relatedAvatarIds: ['a1'],
        subjects: [{ type: 'avatar', id: 'a1', name: 'Alice', color: 'hsl(100, 70%, 65%)' }],
        isMajor: false,
        isStory: true,
      },
    ]

    const wrapper = mount(EventPanel, {
      global: { plugins: [i18n] },
    })

    expect(wrapper.text()).toContain('Alice')
    expect(wrapper.text()).toContain('He sat through the night')
    expect(wrapper.text()).not.toContain('[Alice] He sat through the night')
    expect(wrapper.find('.event-stream-list__subject--avatar').text()).toBe('Alice')
  })

  it('renders subject tag without duplicating story text when text already includes the avatar name', () => {
    const i18n = createEventPanelI18n()

    eventStoreMock.events = [
      {
        id: 'story-with-name',
        text: '',
        content: 'Alice sat through the night and found a trace of insight.',
        year: 1,
        month: 3,
        timestamp: 15,
        relatedAvatarIds: ['a1'],
        subjects: [{ type: 'avatar', id: 'a1', name: 'Alice', color: 'hsl(100, 70%, 65%)' }],
        isMajor: false,
        isStory: true,
      },
    ]

    const wrapper = mount(EventPanel, {
      global: { plugins: [i18n] },
    })

    expect(wrapper.text()).toContain('Alice sat through the night')
    expect(wrapper.text()).not.toContain('[Alice] Alice')
    expect(wrapper.find('.event-stream-list__subject--avatar').text()).toBe('Alice')
  })

  it('renders multiple subject tags for multi-avatar story events', () => {
    const i18n = createEventPanelI18n()

    eventStoreMock.events = [
      {
        id: 'story-multi',
        text: '',
        content: 'They exchanged sword intent below the old gate.',
        year: 1,
        month: 3,
        timestamp: 15,
        relatedAvatarIds: ['a1', 'a2'],
        subjects: [
          { type: 'avatar', id: 'a1', name: 'Alice', color: 'hsl(100, 70%, 65%)' },
          { type: 'avatar', id: 'a2', name: 'Bob', color: 'hsl(200, 70%, 65%)' },
        ],
        isMajor: false,
        isStory: true,
      },
    ]

    const wrapper = mount(EventPanel, {
      global: { plugins: [i18n] },
    })

    expect(wrapper.text()).toContain('They exchanged sword intent below the old gate.')
    expect(wrapper.findAll('.event-stream-list__subject--avatar').map(node => node.text())).toEqual(['Alice', 'Bob'])
  })

  it('clicks structured avatar and sect subject tags', async () => {
    const i18n = createEventPanelI18n()

    eventStoreMock.events = [
      {
        id: 'structured-subjects',
        text: '',
        content: 'A quiet event with no names in the body.',
        year: 1,
        month: 4,
        timestamp: 16,
        relatedAvatarIds: ['a1'],
        relatedSects: [1],
        subjects: [
          { type: 'avatar', id: 'a1', name: 'Alice', color: 'hsl(100, 70%, 65%)' },
          { type: 'sect', id: 1, name: 'Qingyun Sect', color: '#4DD0E1' },
        ],
        isMajor: false,
        isStory: false,
      },
    ]

    const wrapper = mount(EventPanel, {
      global: { plugins: [i18n] },
    })

    const avatarSubject = wrapper.find('.event-stream-list__subject--avatar')
    const sectSubject = wrapper.find('.event-stream-list__subject--sect')

    expect(avatarSubject.text()).toBe('Alice')
    expect(sectSubject.text()).toBe('Qingyun Sect')

    await avatarSubject.trigger('click')
    expect(uiStoreMock.select).toHaveBeenCalledWith('avatar', 'a1')

    await sectSubject.trigger('click')
    expect(uiStoreMock.select).toHaveBeenCalledWith('sect', '1')
  })

  it('renders world subject for events without structured subjects', () => {
    const i18n = createEventPanelI18n()

    eventStoreMock.events = [
      {
        id: 'world-event',
        text: '',
        content: 'A world event happened.',
        year: 1,
        month: 4,
        timestamp: 16,
        relatedAvatarIds: [],
        subjects: [],
        isMajor: false,
        isStory: false,
      },
    ]

    const wrapper = mount(EventPanel, {
      global: { plugins: [i18n] },
    })

    expect(wrapper.find('.event-stream-list__subject--world').text()).toBe('World')
    expect(wrapper.text()).toContain('A world event happened.')
  })

  it('sect filter options use sect_name as label', () => {
    const i18n = createEventPanelI18n()

    const wrapper = mount(EventPanel, {
      global: { plugins: [i18n] }
    })

    const sectSelect = wrapper.findComponent(NSelect)
    expect(sectSelect.exists()).toBe(true)
    const options = sectSelect.props('options') as Array<{ label: string; value: string | number }>
    const sectOptions = options.filter(o => o.value !== 'all')
    expect(sectOptions.map(o => o.label)).toContain('Qingyun Sect')
    expect(sectOptions.map(o => o.label)).toContain('Heavenly Fire Sect')
  })

  it('sect filter options only include active sects', () => {
    sectStoreMock.activeSectOptions = [
      { label: 'Qingyun Sect', value: 1 },
    ]

    const i18n = createEventPanelI18n()

    const wrapper = mount(EventPanel, {
      global: { plugins: [i18n] }
    })

    const sectSelect = wrapper.findComponent(NSelect)
    const options = sectSelect.props('options') as Array<{ label: string; value: string | number }>
    const sectOptions = options.filter(o => o.value !== 'all')
    expect(sectOptions.map(o => o.label)).toEqual(['Qingyun Sect'])
  })

  it('selecting sect filter calls resetEvents with sect_id', async () => {
    const i18n = createEventPanelI18n()

    const wrapper = mount(EventPanel, {
      global: { plugins: [i18n] }
    })

    const sectSelect = wrapper.findComponent(NSelect)
    expect(sectSelect.exists()).toBe(true)
    await sectSelect.vm.$emit('update:value', 1)
    await wrapper.vm.$nextTick()

    expect(eventStoreMock.resetEvents).toHaveBeenCalledWith(expect.objectContaining({ sect_id: 1 }))
  })

  it('major filter options render all three scopes', () => {
    const i18n = createEventPanelI18n()

    const wrapper = mount(EventPanel, {
      global: { plugins: [i18n] }
    })

    const selects = wrapper.findAllComponents(NSelect)
    const majorSelect = selects[selects.length - 1]
    const options = majorSelect.props('options') as Array<{ label: string; value: string }>
    expect(options).toEqual([
      { label: 'All Events', value: 'all' },
      { label: 'Major', value: 'major' },
      { label: 'Minor', value: 'minor' },
    ])
  })

  it('changing major filter calls resetEvents with major_scope', async () => {
    const i18n = createEventPanelI18n()

    const wrapper = mount(EventPanel, {
      global: { plugins: [i18n] }
    })

    const selects = wrapper.findAllComponents(NSelect)
    const majorSelect = selects[selects.length - 1]
    expect(majorSelect.exists()).toBe(true)
    await majorSelect.vm.$emit('update:value', 'major')
    await wrapper.vm.$nextTick()

    expect(eventStoreMock.resetEvents).toHaveBeenCalledWith(expect.objectContaining({ major_scope: 'major' }))
  })

  it('locks event panel to controlled avatar during roleplay', async () => {
    roleplayStoreMock.session.controlled_avatar_id = 'a1'
    const i18n = createEventPanelI18n()

    const wrapper = mount(EventPanel, {
      global: { plugins: [i18n] }
    })

    await wrapper.vm.$nextTick()

    expect(eventStoreMock.resetEvents).toHaveBeenCalledWith(expect.objectContaining({ avatar_id: 'a1' }))

    const selects = wrapper.findAllComponents(NSelect)
    expect(selects[0].props('disabled')).toBeFalsy()
    expect(selects[1].props('disabled')).toBeFalsy()
    expect(wrapper.text()).toContain('Events')
  })

  it('restores previous event filters after leaving roleplay', async () => {
    const i18n = createEventPanelI18n()

    const wrapper = mount(EventPanel, {
      global: { plugins: [i18n] }
    })

    const selects = wrapper.findAllComponents(NSelect)
    const avatarSelect = selects[1]
    await avatarSelect.vm.$emit('update:value', 'a1')
    await wrapper.vm.$nextTick()

    eventStoreMock.resetEvents.mockClear()
    roleplayStoreMock.session.controlled_avatar_id = 'a1'
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    expect(eventStoreMock.resetEvents).toHaveBeenCalledWith(expect.objectContaining({ avatar_id: 'a1' }))

    eventStoreMock.resetEvents.mockClear()
    roleplayStoreMock.session.controlled_avatar_id = null
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    expect(eventStoreMock.resetEvents).toHaveBeenCalledWith(expect.objectContaining({ avatar_id: 'a1' }))
  })
})
