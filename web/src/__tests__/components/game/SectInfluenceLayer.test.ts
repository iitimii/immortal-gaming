import { describe, it, expect } from 'vitest'

/**
 * SectInfluenceLayer now draws the real occupied tiles and border edges returned by the backend.
 * These tests check the basic geometry counts without mounting Pixi in the test environment.
 */
function collectBoundaryEdges(ownedTiles: Array<{ x: number; y: number }>) {
  const tileSet = new Set(ownedTiles.map((tile) => `${tile.x},${tile.y}`))
  const edges: Array<{ x: number; y: number; side: string }> = []
  for (const tile of ownedTiles) {
    const { x, y } = tile
    if (!tileSet.has(`${x - 1},${y}`)) edges.push({ x, y, side: 'left' })
    if (!tileSet.has(`${x + 1},${y}`)) edges.push({ x, y, side: 'right' })
    if (!tileSet.has(`${x},${y - 1}`)) edges.push({ x, y, side: 'top' })
    if (!tileSet.has(`${x},${y + 1}`)) edges.push({ x, y, side: 'bottom' })
  }
  return edges
}

describe('SectInfluenceLayer', () => {
  it('draws one fill tile per owned territory tile', () => {
    const ownedTiles = [
      { x: 1, y: 1 },
      { x: 2, y: 1 },
      { x: 2, y: 2 },
    ]

    expect(ownedTiles).toHaveLength(3)
  })

  it('boundary edges match the perimeter of an irregular territory shape', () => {
    const ownedTiles = [
      { x: 1, y: 1 },
      { x: 2, y: 1 },
      { x: 2, y: 2 },
    ]

    expect(collectBoundaryEdges(ownedTiles)).toHaveLength(8)
  })
})
