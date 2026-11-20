import { ref, onMounted, onUnmounted } from 'vue'
import { useSystemStore } from '@/stores/system'
import { useWorldStore } from '@/stores/world'
import { useSocketStore } from '@/stores/socket'
import { useMapStore } from '@/stores/map'
import { useAvatarStore } from '@/stores/avatar'
import { GAME_PHASES } from '@/constants/game'
import { storeToRefs } from 'pinia'

import { useTextures } from '@/components/game/composables/useTextures'
import { logError, logWarn } from '@/utils/appError'

interface UseGameInitOptions {
  onIdle?: () => void
}

type InitPhaseName =
  | (typeof GAME_PHASES.MAP_READY)[number]
  | (typeof GAME_PHASES.AVATAR_READY)[number]
  | (typeof GAME_PHASES.TEXTURES_READY)[number]

function isPhaseIn(list: readonly string[], phaseName: string): phaseName is InitPhaseName {
  return list.includes(phaseName)
}

export function useGameInit(options: UseGameInitOptions = {}) {
  const systemStore = useSystemStore()
  const worldStore = useWorldStore()
  const mapStore = useMapStore()
  const avatarStore = useAvatarStore()
  const socketStore = useSocketStore()
  const { loadBaseTextures, preloadRegionTextures, preloadAvatarTextures } = useTextures()

  const { initStatus, isInitialized, isLoading } = storeToRefs(systemStore)
  
  // Internal state
  const mapPreloaded = ref(false)
  const avatarsPreloaded = ref(false)
  const texturesPreloaded = ref(false)
  const isInitializingFrontend = ref(false)
  const frontendInitError = ref<string | null>(null)
  const initializeDurationMs = ref(0)
  const lastPollDurationMs = ref(0)
  
  let pollInterval: ReturnType<typeof setInterval> | null = null

  function preloadBaseTexturesOnce() {
    if (texturesPreloaded.value) return
    texturesPreloaded.value = true
    Promise.resolve(loadBaseTextures()).catch((e) => logWarn('GameInit preload textures', e))
  }

  async function preloadMapAndRegionTextures() {
    await worldStore.preloadMap()
    await preloadRegionTextures(mapStore.regions.values())
  }

  // Methods
  async function initializeGame() {
    if (isInitializingFrontend.value) return
    isInitializingFrontend.value = true
    frontendInitError.value = null
    const start = performance.now()
    try {
      if (isInitialized.value) {
        // Reinitialize when a save is reloaded
        worldStore.reset()
      }

      // Initialize the socket connection
      if (!socketStore.isConnected) {
        socketStore.init()
      }

      // Initialize world state
      await worldStore.initialize()
      if (!worldStore.isLoaded) {
        throw new Error('World data was not loaded after initialization')
      }

      // Make sure region and base textures are loaded so the loading phase covers all asset prep.
      await Promise.all([
        preloadRegionTextures(mapStore.regions.values()),
        loadBaseTextures(),
      ])
      await preloadAvatarTextures(avatarStore.avatarList)

      systemStore.setInitialized(true)
      initializeDurationMs.value = performance.now() - start
    } catch (e) {
      frontendInitError.value = e instanceof Error ? e.message : String(e)
      logError('GameInit initialize game', e)
      throw e
    } finally {
      isInitializingFrontend.value = false
    }
  }

  async function pollInitStatus() {
    const pollStart = performance.now()
    try {
      const prevStatus = initStatus.value?.status
      const res = await systemStore.fetchInitStatus()
      
      if (!res) return

      // Idle check
      if (res.status === 'idle') {
        if (prevStatus !== 'idle') {
          options.onIdle?.()
        }
        // If the backend is idle, make sure frontend state is reset too
        if (isInitialized.value) {
            systemStore.setInitialized(false)
            worldStore.reset()
        }
        // Reset preload flags
        mapPreloaded.value = false
        avatarsPreloaded.value = false
        texturesPreloaded.value = false
      }

      // Preload the map
      if (!mapPreloaded.value && isPhaseIn(GAME_PHASES.MAP_READY, res.phase_name)) {
        mapPreloaded.value = true
        Promise.resolve(preloadMapAndRegionTextures()).catch((e) => logWarn('GameInit preload map textures', e))
        preloadBaseTexturesOnce()
      }
      
      // Preload avatars
      if (!avatarsPreloaded.value && isPhaseIn(GAME_PHASES.AVATAR_READY, res.phase_name)) {
        avatarsPreloaded.value = true
        worldStore.preloadAvatars()
      }
      
      // Preload textures (while the backend is still generating)
      if (!texturesPreloaded.value && isPhaseIn(GAME_PHASES.TEXTURES_READY, res.phase_name)) {
        preloadBaseTexturesOnce()
      }
      
      if (res.status === 'ready' && !isInitialized.value && !isInitializingFrontend.value) {
        try {
          await initializeGame()
        } catch {
          // Keep polling; the next ready poll can retry frontend initialization.
        }
        // Keep polling; otherwise state changes after a reset are missed
        // stopPolling()
      }
    } catch (e) {
      logError('GameInit fetch init status', e)
    } finally {
      lastPollDurationMs.value = performance.now() - pollStart
    }
  }

  function startPolling() {
    pollInitStatus()
    pollInterval = setInterval(pollInitStatus, 1000)
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }

  onMounted(() => {
    startPolling()
  })

  onUnmounted(() => {
    stopPolling()
    socketStore.disconnect()
  })

  return {
    initStatus,
    gameInitialized: isInitialized, // Alias for compatibility
    showLoading: isLoading,
    mapPreloaded,
    avatarsPreloaded,
    isInitializingFrontend,
    frontendInitError,
    initializeDurationMs,
    lastPollDurationMs,
    initializeGame,
    startPolling,
    stopPolling
  }
}
