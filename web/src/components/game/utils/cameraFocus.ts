import type { Viewport } from 'pixi-viewport'

/** Pixel size of one map tile; matches the map/entity layers. */
export const MAP_TILE_SIZE = 64

// Mirrors the declaration in Viewport.vue, which publishes the mounted viewport on `window`.
declare global {
  interface Window {
    __viewport?: Viewport
  }
}

type FocusableViewport = Pick<Viewport, 'animate'>

function getActiveViewport(): FocusableViewport | undefined {
  return typeof window === 'undefined' ? undefined : window.__viewport
}

/**
 * Smoothly center the map camera on a tile. Returns false when the map viewport is not mounted.
 */
export function focusCameraOnTile(
  tileX: number,
  tileY: number,
  viewport: FocusableViewport | undefined = getActiveViewport(),
): boolean {
  if (!viewport || !Number.isFinite(tileX) || !Number.isFinite(tileY)) return false

  viewport.animate({
    position: {
      x: tileX * MAP_TILE_SIZE + MAP_TILE_SIZE / 2,
      y: tileY * MAP_TILE_SIZE + MAP_TILE_SIZE / 2,
    },
    time: 350,
    ease: 'easeInOutSine',
    removeOnInterrupt: true,
  })
  return true
}
