import { computed, watch, type Ref } from 'vue'
import { useUiStore } from '@/stores/ui'
import { useSystemStore } from '@/stores/system'
import { useSocketStore } from '@/stores/socket'
import { useRoleplayStore } from '@/stores/roleplay'
import { logError } from '@/utils/appError'
import { storeToRefs } from 'pinia'

interface UseGameControlOptions {
  gameInitialized: Ref<boolean>
  showMenu: Ref<boolean>
  canCloseMenu: Ref<boolean>
  openGameMenu: () => void
  closeMenu: () => void
}

export function useGameControl(options: UseGameControlOptions) {
  const uiStore = useUiStore()
  const systemStore = useSystemStore()
  const socketStore = useSocketStore()
  const roleplayStore = useRoleplayStore()

  const { isManualPaused, simulationSpeed, allowedSpeeds, isStepping } = storeToRefs(systemStore)
  const { isConnected } = storeToRefs(socketStore)

  // Unified pause control:
  // - Menu opened: pause the backend (does not touch isManualPaused)
  // - Menu closed: resume the backend unless manually paused
  watch(options.showMenu, (menuVisible) => {
    if (!options.gameInitialized.value) return
    
    if (menuVisible) {
      systemStore.pause().catch((e) => logError('GameControl pause', e))
    } else {
      if (!isManualPaused.value) {
        systemStore.resume().catch((e) => logError('GameControl resume', e))
      }
    }
  })

  watch(isConnected, (connected, wasConnected) => {
    if (!connected || wasConnected !== false) return
    if (!options.gameInitialized.value) return
    if (options.showMenu.value || isManualPaused.value) return

    systemStore.resume().catch((e) => logError('GameControl resume after reconnect', e))
  })

  // Keyboard shortcuts
  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      if (uiStore.selectedTarget) {
        uiStore.clearSelection()
      } else {
        if (options.showMenu.value) {
          if (options.canCloseMenu.value) {
            options.closeMenu()
          }
        } else {
          options.openGameMenu()
        }
      }
    }
  }

  function toggleManualPause() {
    systemStore.togglePause()
  }

  function setSimulationSpeed(speed: number) {
    systemStore.setSpeed(speed).catch((e) => logError('GameControl set speed', e))
  }

  // The backend rejects manual steps while roleplay waits for player input.
  const isRoleplayWaiting = computed(() => {
    const status = roleplayStore.session.status
    return status !== 'inactive' && status !== 'observing'
  })
  const canStepOnce = computed(() => systemStore.canStepOnce && !isRoleplayWaiting.value)

  function stepOnce() {
    if (!canStepOnce.value) return
    systemStore.stepOnce().catch((e) => logError('GameControl step once', e))
  }

  return {
    isManualPaused,
    simulationSpeed,
    allowedSpeeds,
    handleKeydown,
    toggleManualPause,
    setSimulationSpeed,
    isStepping,
    canStepOnce,
    stepOnce,
  }
}
