import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { systemApi } from '../api';
import type { InitStatusDTO } from '../types/api';
import { logError } from '../utils/appError';

export const useSystemStore = defineStore('system', () => {
  // --- State ---
  const initStatus = ref<InitStatusDTO | null>(null);
  const isInitialized = ref(false); // Frontend initialized (world store loaded, socket connected)
  const isManualPaused = ref(true); // Paused manually by the user
  const isGameRunning = ref(false); // Game is in the Running phase (init status ready)

  // Request counter to handle race conditions.
  let fetchStatusRequestId = 0;
  
  // --- Getters ---
  const isLoading = computed(() => {
    if (!initStatus.value) return true;
    if (initStatus.value.status === 'idle') return false;
    if (initStatus.value.status === 'ready' && isInitialized.value) return false;
    return true;
  });

  const isReady = computed(() => {
    return initStatus.value?.status === 'ready' && isInitialized.value;
  });

  // --- Actions ---
  
  async function fetchInitStatus() {
    const currentRequestId = ++fetchStatusRequestId;
    try {
      const res = await systemApi.fetchInitStatus();
      
      // Only accept the latest response.
      if (currentRequestId !== fetchStatusRequestId) {
        return null;
      }
      
      initStatus.value = res;
      
      if (res.status === 'ready') {
        isGameRunning.value = true;
      } else {
        isGameRunning.value = false;
      }
      return res;
    } catch (e) {
      if (currentRequestId === fetchStatusRequestId) {
        logError('SystemStore fetch init status', e);
      }
      return null;
    }
  }

  function setInitialized(val: boolean) {
    isInitialized.value = val;
  }

  // Toggle manual pause (called from the pause button)
  async function togglePause() {
    const newState = !isManualPaused.value;
    isManualPaused.value = newState;
    try {
      if (newState) {
        await systemApi.pauseGame();
      } else {
        await systemApi.resumeGame();
      }
    } catch (e) {
      // Roll back on API failure
      isManualPaused.value = !newState;
      logError('SystemStore toggle pause', e);
    }
  }

  // Only calls the backend; leaves isManualPaused alone (for system actions like opening/closing the menu)
  async function pause() {
    try {
      await systemApi.pauseGame();
    } catch (e) {
      logError('SystemStore pause', e);
    }
  }

  async function resume() {
    try {
      await systemApi.resumeGame();
    } catch (e) {
      logError('SystemStore resume', e);
    }
  }

  return {
    initStatus,
    isInitialized,
    isManualPaused,
    isGameRunning,
    isLoading,
    isReady,
    
    fetchInitStatus,
    setInitialized,
    togglePause,
    pause,
    resume
  };
});
