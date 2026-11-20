import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { defineComponent, h, ref } from 'vue'
import { useUiStore } from '@/stores/ui'
import { useAvatarStore } from '@/stores/avatar'
import type { AvatarSummary } from '@/types/core'
import {
  closeShortcutHelp,
  getRegisteredShortcuts,
  installKeyboardShortcuts,
  openShortcutHelp,
  useKeyboardShortcuts,
} from '@/composables/useKeyboardShortcuts'
import { useGameShortcuts } from '@/composables/useGameShortcuts'

const focusCameraOnTile = vi.fn((_x: number, _y: number) => true)
vi.mock('@/components/game/utils/cameraFocus', () => ({
  focusCameraOnTile: (x: number, y: number) => focusCameraOnTile(x, y),
}))

function press(key: string, init: KeyboardEventInit = {}, target: EventTarget = window) {
  const event = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...init })
  target.dispatchEvent(event)
  return event
}

let wrapper: VueWrapper | null = null

function setup() {
  const blocked = ref(false)
  const showMenu = ref(false)
  const canCloseMenu = ref(true)
  const simulationSpeed = ref(1)
  const allowedSpeeds = ref([0.5, 1, 2, 4])
  const openGameMenu = vi.fn(() => { showMenu.value = true })
  const closeMenu = vi.fn(() => { showMenu.value = false })
  const toggleManualPause = vi.fn()
  const setSimulationSpeed = vi.fn((speed: number) => { simulationSpeed.value = speed })

  const Host = defineComponent({
    setup() {
      installKeyboardShortcuts({ isGameActive: () => !blocked.value })
      useGameShortcuts({
        showMenu,
        canCloseMenu,
        openGameMenu,
        closeMenu,
        toggleManualPause,
        setSimulationSpeed,
        simulationSpeed,
        allowedSpeeds,
      })
      return () => h('div')
    },
  })
  wrapper = mount(Host, { attachTo: document.body })

  return {
    blocked,
    showMenu,
    canCloseMenu,
    simulationSpeed,
    allowedSpeeds,
    openGameMenu,
    closeMenu,
    toggleManualPause,
    setSimulationSpeed,
  }
}

function openNaiveModal() {
  const container = document.createElement('div')
  container.className = 'n-modal-container'
  const modal = document.createElement('div')
  modal.className = 'n-card n-modal'
  container.appendChild(modal)
  document.body.appendChild(container)
  return modal
}

describe('useGameShortcuts', () => {
  let uiStore: ReturnType<typeof useUiStore>

  beforeEach(() => {
    uiStore = useUiStore()
    focusCameraOnTile.mockClear()
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = null
    closeShortcutHelp()
    document.body.innerHTML = ''
  })

  describe('legacy Escape behaviour', () => {
    it('clears the selection when something is selected', () => {
      const { openGameMenu } = setup()
      uiStore.selectedTarget = { type: 'avatar', id: '123' }

      press('Escape')

      expect(uiStore.selectedTarget).toBeNull()
      expect(openGameMenu).not.toHaveBeenCalled()
    })

    it('opens the game menu when nothing is selected', () => {
      const { openGameMenu } = setup()

      press('Escape')

      expect(openGameMenu).toHaveBeenCalledTimes(1)
    })

    it('closes the menu when it is open and closable', () => {
      const { showMenu, closeMenu, openGameMenu } = setup()
      showMenu.value = true

      press('Escape')

      expect(closeMenu).toHaveBeenCalledTimes(1)
      expect(openGameMenu).not.toHaveBeenCalled()
    })

    it('keeps a non-closable menu open', () => {
      const { showMenu, canCloseMenu, closeMenu, openGameMenu } = setup()
      showMenu.value = true
      canCloseMenu.value = false

      press('Escape')

      expect(closeMenu).not.toHaveBeenCalled()
      expect(openGameMenu).not.toHaveBeenCalled()
    })

    it('still works while focus is inside a text input', () => {
      const { openGameMenu } = setup()
      const input = document.createElement('textarea')
      document.body.appendChild(input)

      press('Escape', {}, input)

      expect(openGameMenu).toHaveBeenCalledTimes(1)
    })

    it('does nothing outside the game scene or while controls are blocked', () => {
      const { blocked, openGameMenu } = setup()
      blocked.value = true
      uiStore.selectedTarget = { type: 'avatar', id: '123' }

      press('Escape')

      expect(uiStore.selectedTarget).not.toBeNull()
      expect(openGameMenu).not.toHaveBeenCalled()
    })
  })

  it('Escape closes the topmost layer only: help overlay, then a Naive modal', () => {
    const { openGameMenu } = setup()
    const { helpVisible } = useKeyboardShortcuts()
    uiStore.selectedTarget = { type: 'avatar', id: '1' }

    openShortcutHelp()
    press('Escape')
    expect(helpVisible.value).toBe(false)
    expect(uiStore.selectedTarget).not.toBeNull()

    const modal = openNaiveModal()
    press('Escape', {}, modal)
    expect(uiStore.selectedTarget).not.toBeNull()
    expect(openGameMenu).not.toHaveBeenCalled()
  })

  it('Space toggles pause', () => {
    const { toggleManualPause } = setup()

    const event = press(' ')

    expect(toggleManualPause).toHaveBeenCalledTimes(1)
    expect(event.defaultPrevented).toBe(true)
  })

  it('gameplay keys are inert while the menu, help overlay or a modal is open', () => {
    const { showMenu, toggleManualPause, setSimulationSpeed } = setup()

    showMenu.value = true
    press(' ')
    press('2')
    showMenu.value = false

    openShortcutHelp()
    press(' ')
    closeShortcutHelp()

    openNaiveModal()
    press('+')

    expect(toggleManualPause).not.toHaveBeenCalled()
    expect(setSimulationSpeed).not.toHaveBeenCalled()
  })

  it('1-4 select the n-th allowed speed', () => {
    const { setSimulationSpeed } = setup()

    press('1')
    press('4')

    expect(setSimulationSpeed).toHaveBeenNthCalledWith(1, 0.5)
    expect(setSimulationSpeed).toHaveBeenNthCalledWith(2, 4)
  })

  it('number keys beyond the allowed speeds are not handled', () => {
    const { allowedSpeeds, setSimulationSpeed } = setup()
    allowedSpeeds.value = [1, 2]

    const event = press('3')

    expect(setSimulationSpeed).not.toHaveBeenCalled()
    expect(event.defaultPrevented).toBe(false)
  })

  it('+ and - step through the allowed speeds and stop at the ends', () => {
    const { simulationSpeed, setSimulationSpeed } = setup()
    simulationSpeed.value = 2

    press('+', { shiftKey: true })
    expect(simulationSpeed.value).toBe(4)
    press('=')
    expect(simulationSpeed.value).toBe(4)

    press('-')
    press('-')
    press('-')
    press('-')
    expect(simulationSpeed.value).toBe(0.5)
    expect(setSimulationSpeed).toHaveBeenCalledTimes(4)
  })

  it('speed keys do nothing until the backend reports allowed speeds', () => {
    const { allowedSpeeds, setSimulationSpeed } = setup()
    allowedSpeeds.value = []

    press('1')
    press('+')

    expect(setSimulationSpeed).not.toHaveBeenCalled()
  })

  it('F focuses the camera on the selected avatar', () => {
    setup()
    const avatarStore = useAvatarStore()
    avatarStore.avatars = new Map([
      ['7', { id: '7', name: 'Lin', x: 12, y: 5 } as AvatarSummary],
    ])

    press('f')
    expect(focusCameraOnTile).not.toHaveBeenCalled()

    uiStore.selectedTarget = { type: 'region', id: '7' }
    press('f')
    expect(focusCameraOnTile).not.toHaveBeenCalled()

    uiStore.selectedTarget = { type: 'avatar', id: '7' }
    press('F', { shiftKey: true })
    expect(focusCameraOnTile).toHaveBeenCalledWith(12, 5)
  })

  it('? toggles the help overlay, but not while the system menu is open', () => {
    const { showMenu } = setup()
    const { helpVisible } = useKeyboardShortcuts()

    press('?', { shiftKey: true })
    expect(helpVisible.value).toBe(true)
    press('?', { shiftKey: true })
    expect(helpVisible.value).toBe(false)

    showMenu.value = true
    press('?', { shiftKey: true })
    expect(helpVisible.value).toBe(false)
  })

  it('registers its shortcuts for the help overlay and removes them on unmount', () => {
    setup()
    const ids = getRegisteredShortcuts().map(shortcut => shortcut.id)

    expect(ids).toEqual(expect.arrayContaining([
      'game.toggle-pause',
      'game.set-speed',
      'game.speed-up',
      'game.speed-down',
      'game.focus-selected-avatar',
      'game.escape',
      'game.toggle-help',
    ]))

    wrapper?.unmount()
    wrapper = null
    expect(getRegisteredShortcuts()).toHaveLength(0)
  })
})
