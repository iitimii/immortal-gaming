import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, nextTick } from 'vue'
import { createI18n } from 'vue-i18n'

const mocks = vi.hoisted(() => ({
  downloadEventExport: vi.fn(),
  saveBlobAsFile: vi.fn(),
}))

vi.mock('naive-ui', async (importOriginal) => {
  const actual = await importOriginal<typeof import('naive-ui')>()
  return {
    ...actual,
    // Inline popover stub: click on the trigger toggles `show`, content renders in place.
    NPopover: defineComponent({
      name: 'NPopover',
      props: ['show', 'trigger', 'placement', 'showArrow'],
      emits: ['update:show'],
      setup(props, { slots, emit }) {
        return () => h('div', { class: 'n-popover-stub' }, [
          h('div', { class: 'popover-trigger', onClick: () => emit('update:show', !props.show) }, slots.trigger?.()),
          props.show ? h('div', { class: 'popover-content' }, slots.default?.()) : null,
        ])
      },
    }),
  }
})

vi.mock('@/api/modules/event', () => ({
  eventApi: { downloadEventExport: mocks.downloadEventExport },
}))

vi.mock('@/stores/avatar', () => ({
  useAvatarStore: () => ({ avatarList: [{ id: 'a1', name: 'Alice', is_dead: false }] }),
}))

vi.mock('@/utils/fileDownload', () => ({
  saveBlobAsFile: mocks.saveBlobAsFile,
}))

vi.mock('@/utils/discreteApi', () => ({
  message: { error: vi.fn() },
}))

import EventExportMenu from '@/components/game/panels/EventExportMenu.vue'

function createTestI18n() {
  return createI18n({
    legacy: false,
    locale: 'en-US',
    messages: {
      'en-US': {
        game: {
          event_panel: {
            export: 'Export',
            export_title: 'Export Chronicle',
            export_format: 'Format',
            export_format_markdown: 'Markdown',
            export_format_json: 'JSON',
            export_scope: 'Scope',
            export_scope_all: 'All events',
            export_scope_avatar: 'Only {avatar}',
            export_scope_major: 'Major events only',
            export_download: 'Download',
            export_failed: 'Export failed: {error}',
          },
        },
      },
    },
  })
}

async function flush() {
  for (let i = 0; i < 5; i += 1) await Promise.resolve()
  await nextTick()
}

function mountMenu(avatarId = '') {
  return mount(EventExportMenu, {
    props: { avatarId },
    global: { plugins: [createTestI18n()] },
  })
}

describe('EventExportMenu', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the export trigger with a hidden menu', () => {
    const wrapper = mountMenu()
    const trigger = wrapper.get('[data-testid="event-export-trigger"]')
    expect(trigger.text()).toBe('Export')
    expect(trigger.find('.event-export-icon').exists()).toBe(true)
    expect(wrapper.find('[data-testid="event-export-menu"]').exists()).toBe(false)
  })

  it('opens the menu with format and scope choices', async () => {
    const wrapper = mountMenu()
    await wrapper.get('[data-testid="event-export-trigger"]').trigger('click')

    const menu = wrapper.get('[data-testid="event-export-menu"]')
    expect(menu.text()).toContain('Markdown')
    expect(menu.text()).toContain('JSON')
    expect(menu.text()).toContain('All events')
    expect(menu.text()).toContain('Major events only')
    expect(menu.text()).not.toContain('Only Alice')
  })

  it('offers the filtered avatar scope', async () => {
    const wrapper = mountMenu('a1')
    await wrapper.get('[data-testid="event-export-trigger"]').trigger('click')
    expect(wrapper.get('[data-testid="event-export-menu"]').text()).toContain('Only Alice')
  })

  it('downloads with the selected options and closes', async () => {
    mocks.downloadEventExport.mockResolvedValue({ blob: new Blob(['x']), filename: 'chronicle-major-year-100.json' })
    const wrapper = mountMenu('a1')
    await wrapper.get('[data-testid="event-export-trigger"]').trigger('click')

    const jsonInput = wrapper
      .findAll('[data-testid="event-export-format"] input')
      .find(input => (input.element as HTMLInputElement).value === 'json')
    const majorInput = wrapper
      .findAll('[data-testid="event-export-scope"] input')
      .find(input => (input.element as HTMLInputElement).value === 'major')
    await jsonInput!.trigger('change')
    await majorInput!.trigger('change')

    await wrapper.get('[data-testid="event-export-submit"]').trigger('click')
    await flush()

    expect(mocks.downloadEventExport).toHaveBeenCalledWith({ format: 'json', major_only: true })
    expect(mocks.saveBlobAsFile).toHaveBeenCalledWith(expect.any(Blob), 'chronicle-major-year-100.json')
    expect(wrapper.find('[data-testid="event-export-menu"]').exists()).toBe(false)
  })
})
