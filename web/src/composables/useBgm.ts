import { watch, effectScope } from 'vue';
import { useSettingStore } from '../stores/setting';
import { withBasePublicPath } from '@/utils/assetUrls';
import { logWarn } from '@/utils/appError';

// Config
const BGM_CONFIG = {
  splash: ['Eastminster.mp3'],
  map: [
    'Healing.mp3', 
    'Ishikari_20Lore.mp3', 
    'PerituneMaterial_Sakuya2.mp3', 
    'PerituneMaterial_Wuxia2_Guzheng_Pipa.mp3'
  ]
};

const FADE_DURATION = 2000; // 2 seconds crossfade

// Types
type BgmType = 'splash' | 'map' | null;

// Module-level state (singleton)
let currentType: BgmType = null;
let activeType: BgmType = null;
let currentTrackIndex = 0; // 0 or 1
let tracks: HTMLAudioElement[] = [];
let initialized = false;
let bag: string[] = []; // Shuffle bag
let currentSwitchId = 0; // Switch request token to prevent concurrent races
let audioUnlocked = false;
let unlockListenersBound = false;

export function useBgm() {
    const settingStore = useSettingStore();

    function init() {
        if (initialized || typeof window === 'undefined') return;
        
        // Create two tracks
        tracks = [new Audio(), new Audio()];
        tracks.forEach((t, i) => {
            t.loop = false; // Looping is handled manually
            t.addEventListener('ended', () => onTrackEnded(i));
        });

        // Watch volume changes in a detached scope so component unmounts do not dispose it
        const scope = effectScope(true);
        scope.run(() => {
            watch(() => settingStore.bgmVolume, (newVol) => {
                updateVolume(newVol);
            });
        });

        // Initialize volume
        updateVolume(settingStore.bgmVolume);
        bindUnlockListeners();

        initialized = true;
    }

    function bindUnlockListeners() {
        if (unlockListenersBound) return;
        unlockListenersBound = true;

        const unlockAudio = () => {
            audioUnlocked = true;
            window.removeEventListener('pointerdown', unlockAudio);
            window.removeEventListener('keydown', unlockAudio);
            unlockListenersBound = false;

            if (currentType && activeType !== currentType) {
                void resumePendingPlayback();
            }
        };

        window.addEventListener('pointerdown', unlockAudio, { once: true });
        window.addEventListener('keydown', unlockAudio, { once: true });
    }

    async function resumePendingPlayback() {
        if (!currentType) return;
        const songName = getNextSong(currentType);
        await switchTrack(songName, activeType !== null);
    }

    function updateVolume(vol: number) {
        tracks.forEach(t => {
            // During a crossfade the animation loop owns the volume; do not interfere
            if (!t.dataset.fading) {
                t.volume = vol;
            }
        });
    }

    // Track ended callback
    function onTrackEnded(index: number) {
        // Only handle the end of the active track
        if (index !== currentTrackIndex) return;

        if (currentType === 'map') {
            // Map mode: track finished naturally, play the next one (no fade-out needed)
            playNextRandom(false); 
        } else if (currentType === 'splash') {
            // Splash mode: loop the single track
            const track = tracks[index];
            track.currentTime = 0;
            track.play().catch(() => {
                activeType = null;
                bindUnlockListeners();
            });
        }
    }

    // Shuffle
    function shuffleBag() {
        if (bag.length === 0) {
            bag = [...BGM_CONFIG.map];
            // Fisher-Yates shuffle
            for (let i = bag.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [bag[i], bag[j]] = [bag[j], bag[i]];
            }
        }
    }

    function getNextSong(type: 'splash' | 'map'): string {
        if (type === 'splash') return BGM_CONFIG.splash[0];
        
        if (bag.length === 0) shuffleBag();
        return bag.pop()!;
    }

    // Main play API
    async function play(type: BgmType) {
        if (!initialized) init();
        
        // Stop playback when given null or empty
        if (!type) {
            stop();
            return;
        }
        
        // Ignore if the same type is already playing
        if (currentType === type && activeType === type) return;

        currentType = type;
        if (!audioUnlocked) {
            bindUnlockListeners();
            return;
        }

        const songName = getNextSong(type);
        // When switching type the old track is playing and must fade out
        await switchTrack(songName, activeType !== null);
    }

    // Play the next random track (map mode only)
    async function playNextRandom(crossfadeOutgoing: boolean = true) {
        if (currentType !== 'map') return;
        const songName = getNextSong('map');
        await switchTrack(songName, crossfadeOutgoing);
    }

    // Core track-switch logic
    async function switchTrack(songName: string, crossfadeOutgoing: boolean) {
        const url = withBasePublicPath(`bgm/${songName}`);
        const nextIndex = (currentTrackIndex + 1) % 2;
        const nextTrack = tracks[nextIndex];
        const currentTrack = tracks[currentTrackIndex];

        nextTrack.src = url;
        nextTrack.volume = 0; // Fade in from silence
        
        currentSwitchId++;
        const mySwitchId = currentSwitchId;
        
        try {
            await nextTrack.play();
            // If a new switch started while awaiting play(), drop this one
            if (mySwitchId !== currentSwitchId) {
                nextTrack.pause();
                return;
            }
            performCrossfade(nextTrack, currentTrack, crossfadeOutgoing, mySwitchId);
            currentTrackIndex = nextIndex;
            activeType = currentType;
        } catch (e: unknown) {
            if (mySwitchId !== currentSwitchId) return;
            const errorName = e instanceof Error ? e.name : '';

            if (errorName === 'NotAllowedError') {
                activeType = null;
                audioUnlocked = false;
                currentTrack.pause();
                bindUnlockListeners();
                return;
            }

            if (errorName === 'AbortError') {
                return;
            }

            logWarn('Bgm switch track', e);
        }
    }

    // Crossfade animation
    function performCrossfade(fadeIn: HTMLAudioElement, fadeOut: HTMLAudioElement, fadeOutEnabled: boolean, mySwitchId: number) {
        const start = performance.now();
        // remove static targetVol capture
        
        fadeIn.dataset.fading = 'true';
        if (fadeOutEnabled) fadeOut.dataset.fading = 'true';

        function step(now: number) {
            // Abort the current crossfade if a newer switch was requested
            if (mySwitchId !== currentSwitchId) {
                delete fadeIn.dataset.fading;
                if (fadeOutEnabled) delete fadeOut.dataset.fading;
                return;
            }

            const elapsed = now - start;
            const progress = Math.min(elapsed / FADE_DURATION, 1);
            const currentTargetVol = settingStore.bgmVolume; // Dynamic volume check

            // Fade in
            const newFadeInVol = progress * currentTargetVol;
            if (newFadeInVol >= 0 && newFadeInVol <= 1) {
                fadeIn.volume = newFadeInVol;
            }

            // Fade out
            if (fadeOutEnabled && !fadeOut.paused) {
                const newFadeOutVol = Math.max(0, (1 - progress) * currentTargetVol);
                if (newFadeOutVol >= 0 && newFadeOutVol <= 1) {
                    fadeOut.volume = newFadeOutVol;
                }
            }

            if (progress < 1) {
                requestAnimationFrame(step);
            } else {
                // Animation finished
                delete fadeIn.dataset.fading;
                if (fadeOutEnabled) delete fadeOut.dataset.fading;
                
                if (fadeOutEnabled) {
                    fadeOut.pause();
                    fadeOut.currentTime = 0;
                }
                // Make sure the final volume is exact
                fadeIn.volume = settingStore.bgmVolume;
            }
        }
        requestAnimationFrame(step);
    }

    function stop() {
        if (!initialized) return;
        currentType = null;
        activeType = null;
        currentSwitchId++;
        const mySwitchId = currentSwitchId;

        tracks.forEach(t => {
             // Quick fade-out, then stop
             const startVol = t.volume;
             const start = performance.now();
             
             // Mark as fading so the volume watcher stays out of the way
             t.dataset.fading = 'true';

             function fade(now: number) {
                 if (mySwitchId !== currentSwitchId) {
                     delete t.dataset.fading;
                     return;
                 }

                 const progress = Math.min((now - start) / 1000, 1); // 1s fade-out
                 t.volume = Math.max(0, startVol * (1 - progress));
                 
                 if (progress < 1) {
                     requestAnimationFrame(fade);
                 } else {
                     t.pause();
                     t.currentTime = 0;
                     delete t.dataset.fading;
                 }
             }
             if(!t.paused) requestAnimationFrame(fade);
        });
    }

    return { init, play, stop };
}
