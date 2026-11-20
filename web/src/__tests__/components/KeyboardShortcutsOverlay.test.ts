import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { defineComponent, h, nextTick, ref } from 'vue'
import KeyboardShortcutsOverlay from '@/components/KeyboardShortcutsOverlay.vue'
import SystemMenuOtherTab from '@/components/system-menu/tabs/SystemMenuOtherTab.vue'
import {
  closeShortcutHelp,
  installKeyboardShortcuts,
  openShortcutHelp,
  useKeyboardShortcuts,
} from '@/composables/useKeyboardShortcuts'
import { useGameShortcuts } from '@/composables/useGameShortcuts'
import { createTestI18n } from '@/__tests__/utils/i18n'
import shortcutsMessages from '@/locales/en-US/shortcuts.json'

const i18n = createTestI18n({
  shortcuts: shortcutsMessages,
  ui: {
    other_options: 'Other Options',
    other_options_desc: 'Manage game process and exit.',
    return_to_main: 'Return',
    return_to_main_desc: 'Return desc',
    quit_game: 'Quit',
    quit_game_desc: 'Quit desc',
  },
})

const mountOptions = {
  attachTo: document.body,
  global: {
    plugins: [i18n],
    directives: { sound: () => {} },
  },
}

let wrappers: VueWrapper[] = []

function mountOverlayWithGameShortcuts() {
  const Host = defineComponent({
    setup() {
      installKeyboardShortcuts({ isGameActive: () => true })
      useGameShortcuts({
        showMenu: ref(false),
        canCloseMenu: ref(true),
        openGameMenu: vi.fn(),
        closeMenu: vi.fn(),
        toggleManualPause: vi.fn(),
        setSimulationSpeed: vi.fn(),
        simulationSpeed: ref(1),
        allowedSpeeds: ref([1, 2]),
      })
      return () => h(KeyboardShortcutsOverlay)
    },
  })
  const wrapper = mount(Host, mountOptions)
  wrappers.push(wrapper)
  return wrapper
}

afterEach(() => {
  wrappers.forEach(wrapper => wrapper.unmount())
  wrappers = []
  closeShortcutHelp()
  document.body.innerHTML = ''
})

describe('KeyboardShortcutsOverlay', () => {
  it('renders nothing while hidden', () => {
    const wrapper = mountOverlayWithGameShortcuts()

    expect(wrapper.find('.shortcuts-overlay').exists()).toBe(false)
  })

  it('lists the registered shortcuts grouped by group key', async () => {
    const wrapper = mountOverlayWithGameShortcuts()
    openShortcutHelp()
    await nextTick()

    const groups = wrapper.findAll('.shortcuts-group')
    expect(groups.map(group => group.find('h3').text())).toEqual(['Simulation', 'Map', 'General'])

    const pauseRow = wrapper.find('[data-shortcut="game.toggle-pause"]')
    expect(pauseRow.text()).toContain('Pause / resume')
    expect(pauseRow.findAll('kbd').map(kbd => kbd.text())).toEqual(['Space'])

    const speedRow = wrapper.find('[data-shortcut="game.set-speed"]')
    expect(speedRow.findAll('kbd').map(kbd => kbd.text())).toEqual(['1', '2', '3', '4'])

    expect(wrapper.find('[data-shortcut="game.escape"] kbd').text()).toBe('Esc')
    expect(wrapper.find('[data-shortcut="shortcuts.close-help"]').exists()).toBe(false)
  })

  it('shows shortcuts registered later by other features', async () => {
    const wrapper = mountOverlayWithGameShortcuts()
    const unregister = useKeyboardShortcuts().register([{
      id: 'game.extra',
      keys: ['x'],
      labelKey: 'shortcuts.actions.speed_up',
      groupKey: 'shortcuts.groups.simulation',
      handler: () => {},
    }])
    openShortcutHelp()
    await nextTick()

    const simulation = wrapper.find('[data-group="shortcuts.groups.simulation"]')
    expect(simulation.find('[data-shortcut="game.extra"] kbd').text()).toBe('x')
    unregister()
  })

  it('closes from the close button, a click outside, Escape and ?', async () => {
    const wrapper = mountOverlayWithGameShortcuts()
    const { helpVisible } = useKeyboardShortcuts()

    openShortcutHelp()
    await nextTick()
    await wrapper.find('.shortcuts-close').trigger('click')
    expect(helpVisible.value).toBe(false)

    openShortcutHelp()
    await nextTick()
    await wrapper.find('.shortcuts-panel').trigger('click')
    expect(helpVisible.value).toBe(true)
    await wrapper.find('.shortcuts-overlay').trigger('click')
    expect(helpVisible.value).toBe(false)

    openShortcutHelp()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', cancelable: true }))
    expect(helpVisible.value).toBe(false)

    openShortcutHelp()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: '?', shiftKey: true, cancelable: true }))
    expect(helpVisible.value).toBe(false)
  })
})

describe('SystemMenuOtherTab shortcuts entry', () => {
  it('emits show-shortcuts when the entry is clicked', async () => {
    const wrapper = mount(SystemMenuOtherTab, mountOptions)
    wrappers.push(wrapper)

    const entry = wrapper.find('.shortcuts-entry')
    expect(entry.text()).toContain('Keyboard Shortcuts')
    await entry.trigger('click')

    expect(wrapper.emitted('show-shortcuts')).toHaveLength(1)
  })
})
