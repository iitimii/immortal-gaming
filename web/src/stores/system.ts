import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { systemApi } from '../api';
import type { InitStatusDTO, StepOnceResponseDTO } from '../types/api';
import { logError } from '../utils/appError';

export const useSystemStore = defineStore('system', () => {
  // --- State ---
  const initStatus = ref<InitStatusDTO | null>(null);
  const isInitialized = ref(false); // Frontend initialized (world store loaded, socket connected)
  const isManualPaused = ref(true); // Paused manually by the user
  const isGameRunning = ref(false); // Game is in the Running phase (init status ready)
  const simulationSpeed = ref(1); // Runtime speed multiplier, synced from the backend
  const allowedSpeeds = ref<number[]>([]); // Backend-provided speed options
  const isStepping = ref(false); // A manual "step one month" request is in flight

  // Request counter to handle race conditions.
  let fetchStatusRequestId = 0;
  // Bumped on every local speed change so in-flight status polls cannot revert it.
  let speedChangeSeq = 0;
  let pendingSpeedRequests = 0;
  
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

  // Manual stepping is only offered while the user has paused a ready game.
  const canStepOnce = computed(() => isReady.value && isManualPaused.value && !isStepping.value);

  // --- Actions ---
  
  async function fetchInitStatus() {
    const currentRequestId = ++fetchStatusRequestId;
    const speedSeqAtRequest = speedChangeSeq;
    try {
      const res = await systemApi.fetchInitStatus();
      
      // Only accept the latest response.
      if (currentRequestId !== fetchStatusRequestId) {
        return null;
      }
      
      initStatus.value = res;
      if (speedSeqAtRequest === speedChangeSeq && pendingSpeedRequests === 0) {
        applySpeedState(res.speed, res.allowed_speeds);
      }
      
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

  function applySpeedState(speed?: number, allowed?: number[]) {
    if (Array.isArray(allowed) && allowed.length > 0) {
      allowedSpeeds.value = allowed;
    }
    if (typeof speed === 'number' && Number.isFinite(speed) && speed > 0) {
      simulationSpeed.value = speed;
    }
  }

  async function setSpeed(speed: number) {
    if (speed === simulationSpeed.value) return;
    const previous = simulationSpeed.value;
    simulationSpeed.value = speed;
    speedChangeSeq += 1;
    pendingSpeedRequests += 1;
    try {
      const res = await systemApi.setSpeed(speed);
      applySpeedState(res.speed, res.allowed_speeds);
    } catch (e) {
      // Roll back unless a newer change has already replaced this one.
      if (simulationSpeed.value === speed) {
        simulationSpeed.value = previous;
      }
      logError('SystemStore set speed', e);
    } finally {
      pendingSpeedRequests -= 1;
      speedChangeSeq += 1;
    }
  }

  // Advance the paused world by exactly one month. The tick itself arrives over
  // the websocket like a normal loop step; the response only summarises it.
  async function stepOnce(): Promise<StepOnceResponseDTO | null> {
    if (!canStepOnce.value) return null;
    isStepping.value = true;
    try {
      return await systemApi.stepOnce();
    } catch (e) {
      logError('SystemStore step once', e);
      return null;
    } finally {
      isStepping.value = false;
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
    simulationSpeed,
    allowedSpeeds,
    isStepping,
    isLoading,
    isReady,
    canStepOnce,
    
    fetchInitStatus,
    setInitialized,
    togglePause,
    setSpeed,
    stepOnce,
    pause,
    resume
  };
});
