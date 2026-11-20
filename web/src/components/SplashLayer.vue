<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { NButton } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useBgm } from '../composables/useBgm'
import { withBasePublicPath } from '@/utils/assetUrls'

// Events
const emit = defineEmits<{
  (e: 'action', key: string): void
}>()

const { t } = useI18n()
const videoRef = ref<HTMLVideoElement | null>(null)
const splashPosterUrl = withBasePublicPath('assets/splash.png')
const splashVideoUrl = withBasePublicPath('assets/splash.mp4')

// Video playback control
onMounted(() => {
  // Play background music
  useBgm().play('splash')

  if (!videoRef.value) return
  
  const video = videoRef.value
  // Base playback rate 0.8
  video.playbackRate = 0.8

  const handleTimeUpdate = () => {
    const duration = video.duration
    if (!duration) return

    const remaining = duration - video.currentTime
    
    // Slow down linearly in the last 2 seconds
    if (remaining < 2 && remaining > 0) {
      // Ease from 0.8 down to about 0.35 to avoid a choppy look
      const targetRate = 0.35 + (0.8 - 0.35) * (remaining / 2)
      video.playbackRate = targetRate
    }
  }

  video.addEventListener('timeupdate', handleTimeUpdate)
})

// Menu buttons
const menuOptions = computed(() => [
  { label: t('ui.start_game'), subLabel: t('splash.subtitle_start_en'), key: 'start', disabled: false },
  { label: t('ui.load_game'), subLabel: t('splash.subtitle_load_en'), key: 'load', disabled: false },
  { label: t('ui.achievements'), subLabel: t('splash.subtitle_achievements_en'), key: 'achievements', disabled: true },
  { label: t('ui.settings'), subLabel: t('splash.subtitle_settings_en'), key: 'settings', disabled: false },
  { label: t('ui.about'), subLabel: t('splash.subtitle_about_en'), key: 'about', disabled: false },
  { label: t('ui.exit'), subLabel: t('splash.subtitle_exit_en'), key: 'exit', disabled: false }
])

function handleClick(key: string) {
  emit('action', key)
}
</script>

<template>
  <div class="splash-container">
    <video
      ref="videoRef"
      class="splash-video"
      autoplay
      muted
      playsinline
      :poster="splashPosterUrl"
    >
      <source :src="splashVideoUrl" type="video/mp4" />
    </video>
    <!-- Left blur panel -->
    <div class="glass-panel">
      <div class="title-area">
        <h1>{{ t('splash.title') }}</h1>
        <p>{{ t('splash.tagline_en') }}</p>
      </div>
      
      <div class="menu-area">
        <div class="menu-stack">
          <n-button
            v-for="opt in menuOptions"
            :key="opt.key"
            size="large"
            block
            color="#ffffff20"
            text-color="#fff"
            class="menu-btn"
            :disabled="opt.disabled"
            v-sound="'click'"
            @click="handleClick(opt.key)"
          >
            <div class="btn-content">
              <span class="btn-label">{{ opt.label }}</span>
              <span class="btn-sub">{{ opt.subLabel }}</span>
            </div>
          </n-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.splash-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 500;
  display: flex;
  align-items: center;
  background-color: #000; /* Background before the video loads */
  overflow: hidden;
}

.splash-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 0;
}

/* Left frosted-glass panel */
.glass-panel {
  position: relative;
  z-index: 1;
  box-sizing: border-box;
  width: clamp(360px, 42vw, 460px);
  height: 100%;
  background: rgba(0, 0, 0, 0.4); /* Translucent black */
  backdrop-filter: blur(20px); /* Main blur effect */
  -webkit-backdrop-filter: blur(20px);
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: clamp(32px, 6vh, 72px) clamp(32px, 5vw, 60px);
  box-shadow: 10px 0 30px rgba(0, 0, 0, 0.5);
}

.title-area {
  color: #fff;
  text-shadow: 0 2px 4px rgba(0,0,0,0.5);
}

.title-area h1 {
  font-size: clamp(2.15rem, 5.1vh, 3rem);
  line-height: 1.22;
  margin-bottom: 10px;
  font-weight: bold;
  letter-spacing: clamp(1px, 0.35vw, 4px);
  overflow-wrap: break-word;
}

.title-area p {
  font-size: clamp(1rem, 2.1vh, 1.2rem);
  line-height: 1.45;
  opacity: 0.8;
  letter-spacing: clamp(1px, 0.2vw, 2px);
}

.menu-area {
  width: 100%;
}

.menu-stack {
  display: flex;
  flex-direction: column;
  gap: clamp(8px, 1.4vh, 16px);
}

/* Button tweaks */
.menu-btn {
  height: clamp(50px, 6.3vh, 60px); /* Shrinks with viewport height so long labels stay above the fold */
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
  
  /* Key fix: force left-aligned content */
  justify-content: flex-start;
  text-align: left;
  padding-left: clamp(22px, 3vw, 32px); /* Consistent left padding */
}

/* Override Naive UI centering button content by default */
.menu-btn :deep(.n-button__content) {
  justify-content: flex-start;
  width: 100%;
}

.btn-content {
  display: flex;
  flex-direction: column;
  align-items: flex-start; /* Left-align */
  width: 100%;
}

.btn-label {
  max-width: 100%;
  font-size: clamp(16px, 2.1vh, 20px);
  letter-spacing: clamp(1px, 0.28vw, 4px);
  line-height: 1.2;
  white-space: normal;
  overflow-wrap: anywhere;
}

.btn-sub {
  font-size: 10px;
  opacity: 0.6;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.menu-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.25);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateX(10px);
  box-shadow: 0 0 15px rgba(255, 255, 255, 0.1);
}

/* Basic mobile adjustments (the game is mainly for desktop) */
@media (max-width: 768px) {
  .glass-panel {
    width: min(100%, 420px);
    border-right: none;
    background: rgba(0, 0, 0, 0.6);
  }
}

@media (max-height: 760px) {
  .glass-panel {
    padding-block: 24px;
  }

  .title-area h1 {
    font-size: clamp(1.9rem, 4.8vh, 2.4rem);
  }

  .menu-stack {
    gap: 8px;
  }

  .menu-btn {
    height: 48px;
  }
}
</style>
