import { useSettingStore } from '../stores/setting';
import { withBasePublicPath } from '@/utils/assetUrls';
import { logWarn } from '@/utils/appError';

// Sound assets (ogg)
const SOUND_URLS = {
  click: withBasePublicPath('sfx/click.ogg'),
  cancel: withBasePublicPath('sfx/cancel.ogg'),
  select: withBasePublicPath('sfx/select.ogg'),
  open: withBasePublicPath('sfx/open.ogg'),
} as const;

export type SoundType = keyof typeof SOUND_URLS;

// Singleton AudioContext and buffers
let audioContext: AudioContext | null = null;
const buffers: Partial<Record<SoundType, AudioBuffer>> = {};

type AudioContextConstructor = new () => AudioContext;
type AudioWindow = typeof window & {
  webkitAudioContext?: AudioContextConstructor;
};

export function useAudio() {
  const settingStore = useSettingStore();

  // 1. Init and preload (call when main.ts or App.vue mounts)
  async function init() {
    if (typeof window === 'undefined') return;

    if (!audioContext) {
      const audioWindow = window as AudioWindow;
      const AudioContextClass = audioWindow.AudioContext || audioWindow.webkitAudioContext;
      if (AudioContextClass) {
          audioContext = new AudioContextClass();
      } else {
          logWarn('Audio init unsupported', 'Web Audio API is not supported in this browser.');
          return;
      }
    }
    
    // Preload all sounds
    const loadPromises = Object.entries(SOUND_URLS).map(async ([key, url]) => {
      if (buffers[key as SoundType]) return; // Skip already loaded

      try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const arrayBuffer = await response.arrayBuffer();
        if (audioContext) {
            const decodedBuffer = await audioContext.decodeAudioData(arrayBuffer);
            buffers[key as SoundType] = decodedBuffer;
        }
      } catch (e) {
        logWarn(`Audio load sound ${key}`, e);
      }
    });

    await Promise.all(loadPromises);
  }

  // 2. Playback
  function play(type: SoundType = 'click') {
    if (settingStore.sfxVolume <= 0 || !audioContext || !buffers[type]) return;

    // Browser policy: a suspended context (common before any user interaction) must be resumed
    // resume() must be called from a user interaction
    if (audioContext.state === 'suspended') {
      Promise.resolve(audioContext.resume()).catch((e) => logWarn('Audio resume context', e));
    }

    const source = audioContext.createBufferSource();
    const gainNode = audioContext.createGain();
    if (!source || !gainNode) {
      logWarn('Audio play unavailable', `Missing audio nodes for sound: ${type}`);
      return;
    }

    source.buffer = buffers[type]!;
    
    // Gain node for volume
    gainNode.gain.value = settingStore.sfxVolume;
    
    source.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    source.start(0); // Play immediately
  }

  return { init, play };
}
