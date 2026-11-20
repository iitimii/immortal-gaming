<script setup lang="ts">
import { Application } from 'vue3-pixi'
import { ref, onMounted } from 'vue'
import { useElementSize } from '@vueuse/core'
import Viewport from './Viewport.vue'
import MapLayer from './MapLayer.vue'
import EntityLayer from './EntityLayer.vue'
import POILayer from './POILayer.vue'
import PerceptionLayer from './PerceptionLayer.vue'
import SectInfluenceLayer from './SectInfluenceLayer.vue'
import CloudLayer from './CloudLayer.vue'
import { useTextures } from './composables/useTextures'

const container = ref<HTMLElement>()
const { width, height } = useElementSize(container)
const { loadBaseTextures, isLoaded } = useTextures()

const mapSize = ref({ width: 2000, height: 2000 })

defineProps<{
  sidebarWidth?: number
}>()

const emit = defineEmits<{
  (e: 'avatarSelected', payload: { type: 'avatar'; id: string; name?: string }): void
  (e: 'regionSelected', payload: { type: 'region'; id: string; name?: string }): void
  (e: 'poiSelected', payload: { type: 'avatar' | 'poi'; id: string; kind?: string; name?: string }): void
}>()

function onMapLoaded(size: { width: number, height: number }) {
    mapSize.value = size
}

function handleAvatarSelected(payload: { type: 'avatar'; id: string; name?: string }) {
  emit('avatarSelected', payload)
}

function handleRegionSelected(payload: { type: 'region'; id: string; name?: string }) {
  emit('regionSelected', payload)
}

function handlePoiSelected(payload: { type: 'avatar' | 'poi'; id: string; kind?: string; name?: string }) {
  emit('poiSelected', payload)
}

const devicePixelRatio = 1 // Force 1 to avoid coordinate/scaling issues for pixel art on high-DPI screens

onMounted(() => {
  loadBaseTextures()
})
</script>

<template>
  <div ref="container" class="game-canvas-container">
    <!-- 
      antialias: false (must be off for pixel art)
      resolution: devicePixelRatio (keeps it crisp)
      background-color: 0x000000
    -->
    <Application
      v-if="width > 0 && height > 0"
      :width="width"
      :height="height"
      :resizeTo="container"
      :background-color="0x000000"
      :antialias="false"
      :resolution="devicePixelRatio"
    >
      <Viewport
        v-if="isLoaded"
        :screen-width="width"
        :screen-height="height"
        :world-width="mapSize.width"
        :world-height="mapSize.height"
      >
        <!-- 
          Note: the old store.worldVersion has been removed.
          Re-rendering MapLayer (e.g. after loading a save)
          now relies on worldStore.initialize() changing mapData,
          plus MapLayer's own watcher on worldStore.isLoaded.
          If loading a save does not refresh it, add a key to MapLayer.
        -->
        <MapLayer 
          @mapLoaded="onMapLoaded" 
          @regionSelected="handleRegionSelected" 
        />
        <SectInfluenceLayer :width="mapSize.width" :height="mapSize.height" />
        <POILayer @poiSelected="handlePoiSelected" />
        <EntityLayer @avatarSelected="handleAvatarSelected" />
        <PerceptionLayer :width="mapSize.width" :height="mapSize.height" />
        <CloudLayer :width="mapSize.width" :height="mapSize.height" />
      </Viewport>
    </Application>
  </div>
</template>

<style scoped>
.game-canvas-container {
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #000;
}

.game-canvas-container :deep(canvas) {
  display: block;
}
</style>
