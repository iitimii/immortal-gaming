import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, ref } from 'vue'
import { useUiStore } from '@/stores/ui'
import { useSocketStore } from '@/stores/socket'
import { useSystemStore } from '@/stores/system'
import { useRoleplayStore } from '@/stores/roleplay'
import { useGameControl } from '@/composables/useGameControl'

const createTestComponent = () => {
  const showMenu = ref(false)
  const canCloseMenu = ref(true)
  const gameInitialized = ref(false)
  const openGameMenu = vi.fn(() => {
    showMenu.value = true
  })
  const closeMenu = vi.fn(() => {
    showMenu.value = false
  })

  const component = defineComponent({
    setup() {
      return useGameControl({
        gameInitialized,
        showMenu,
        canCloseMenu,
        openGameMenu,
        closeMenu,
      })
    },
    template: '<div></div>',
  })

  return { component, showMenu, canCloseMenu, gameInitialized, openGameMenu, closeMenu }
}

describe('useGameControl', () => {
  let uiStore: ReturnType<typeof useUiStore>
  let socketStore: ReturnType<typeof useSocketStore>
  let systemStore: ReturnType<typeof useSystemStore>

  beforeEach(() => {
    uiStore = useUiStore()
    socketStore = useSocketStore()
    systemStore = useSystemStore()
    vi.clearAllMocks()
  })

  it('clears selection when Escape pressed and target selected', () => {
    const { component } = createTestComponent()
    const wrapper = mount(component)

    uiStore.selectedTarget = { type: 'avatar', id: '123' }

    wrapper.vm.handleKeydown(new KeyboardEvent('keydown', { key: 'Escape' }))

    expect(uiStore.selectedTarget).toBeNull()
    wrapper.unmount()
  })

  it('opens game menu when Escape pressed without selection', () => {
    const { component, gameInitialized, openGameMenu } = createTestComponent()
    gameInitialized.value = true
    const wrapper = mount(component)

    wrapper.vm.handleKeydown(new KeyboardEvent('keydown', { key: 'Escape' }))

    expect(openGameMenu).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('closes menu when Escape pressed and menu is closable', () => {
    const { component, gameInitialized, showMenu, canCloseMenu, closeMenu } = createTestComponent()
    gameInitialized.value = true
    showMenu.value = true
    canCloseMenu.value = true
    const wrapper = mount(component)

    wrapper.vm.handleKeydown(new KeyboardEvent('keydown', { key: 'Escape' }))

    expect(closeMenu).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('does not close menu when Escape pressed and menu is not closable', () => {
    const { component, gameInitialized, showMenu, canCloseMenu, closeMenu } = createTestComponent()
    gameInitialized.value = true
    showMenu.value = true
    canCloseMenu.value = false
    const wrapper = mount(component)

    wrapper.vm.handleKeydown(new KeyboardEvent('keydown', { key: 'Escape' }))

    expect(closeMenu).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('pauses and resumes backend when menu visibility changes after initialization', async () => {
    const pauseSpy = vi.spyOn(systemStore, 'pause').mockResolvedValue(undefined)
    const resumeSpy = vi.spyOn(systemStore, 'resume').mockResolvedValue(undefined)
    const { component, gameInitialized, showMenu } = createTestComponent()
    gameInitialized.value = true
    systemStore.isManualPaused = false
    const wrapper = mount(component)

    showMenu.value = true
    await Promise.resolve()
    showMenu.value = false
    await Promise.resolve()

    expect(pauseSpy).toHaveBeenCalledTimes(1)
    expect(resumeSpy).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('toggles manual pause via system store', () => {
    const togglePauseSpy = vi.spyOn(systemStore, 'togglePause').mockResolvedValue(undefined)
    const { component } = createTestComponent()
    const wrapper = mount(component)

    wrapper.vm.toggleManualPause()

    expect(togglePauseSpy).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('exposes simulation speed state and forwards speed changes to the system store', () => {
    const setSpeedSpy = vi.spyOn(systemStore, 'setSpeed').mockResolvedValue(undefined)
    systemStore.simulationSpeed = 2
    systemStore.allowedSpeeds = [0.5, 1, 2, 4]
    const { component } = createTestComponent()
    const wrapper = mount(component)

    expect(wrapper.vm.simulationSpeed).toBe(2)
    expect(wrapper.vm.allowedSpeeds).toEqual([0.5, 1, 2, 4])

    wrapper.vm.setSimulationSpeed(4)

    expect(setSpeedSpy).toHaveBeenCalledWith(4)
    wrapper.unmount()
  })

  describe('step once', () => {
    function makeStoreSteppable() {
      systemStore.initStatus = {
        status: 'ready',
        phase: 0,
        phase_name: '',
        progress: 100,
        elapsed_seconds: 0,
        error: null,
        llm_check_failed: false,
        llm_error_message: '',
      }
      systemStore.setInitialized(true)
      systemStore.isManualPaused = true
    }

    it('forwards stepOnce to the system store when stepping is allowed', () => {
      const stepSpy = vi.spyOn(systemStore, 'stepOnce').mockResolvedValue(null)
      makeStoreSteppable()
      const { component } = createTestComponent()
      const wrapper = mount(component)

      expect(wrapper.vm.canStepOnce).toBe(true)
      wrapper.vm.stepOnce()

      expect(stepSpy).toHaveBeenCalledTimes(1)
      wrapper.unmount()
    })

    it('disables stepping while the game is running', () => {
      const stepSpy = vi.spyOn(systemStore, 'stepOnce').mockResolvedValue(null)
      makeStoreSteppable()
      systemStore.isManualPaused = false
      const { component } = createTestComponent()
      const wrapper = mount(component)

      expect(wrapper.vm.canStepOnce).toBe(false)
      wrapper.vm.stepOnce()

      expect(stepSpy).not.toHaveBeenCalled()
      wrapper.unmount()
    })

    it('disables stepping while roleplay waits for player input', () => {
      const stepSpy = vi.spyOn(systemStore, 'stepOnce').mockResolvedValue(null)
      makeStoreSteppable()
      const roleplayStore = useRoleplayStore()
      roleplayStore.session = { ...roleplayStore.session, status: 'awaiting_decision' }
      const { component } = createTestComponent()
      const wrapper = mount(component)

      expect(wrapper.vm.canStepOnce).toBe(false)
      wrapper.vm.stepOnce()

      expect(stepSpy).not.toHaveBeenCalled()
      wrapper.unmount()
    })

    it('exposes the busy state from the system store', () => {
      makeStoreSteppable()
      systemStore.isStepping = true
      const { component } = createTestComponent()
      const wrapper = mount(component)

      expect(wrapper.vm.isStepping).toBe(true)
      expect(wrapper.vm.canStepOnce).toBe(false)
      wrapper.unmount()
    })
  })

  it('resumes backend after websocket reconnect when game is active and not manually paused', async () => {
    const resumeSpy = vi.spyOn(systemStore, 'resume').mockResolvedValue(undefined)
    const { component, gameInitialized, showMenu } = createTestComponent()
    gameInitialized.value = true
    showMenu.value = false
    systemStore.isManualPaused = false
    const wrapper = mount(component)

    socketStore.isConnected = false
    await Promise.resolve()
    socketStore.isConnected = true
    await Promise.resolve()

    expect(resumeSpy).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('does not auto-resume after reconnect when user has manually paused', async () => {
    const resumeSpy = vi.spyOn(systemStore, 'resume').mockResolvedValue(undefined)
    const { component, gameInitialized } = createTestComponent()
    gameInitialized.value = true
    systemStore.isManualPaused = true
    const wrapper = mount(component)

    socketStore.isConnected = false
    await Promise.resolve()
    socketStore.isConnected = true
    await Promise.resolve()

    expect(resumeSpy).not.toHaveBeenCalled()
    wrapper.unmount()
  })
})
