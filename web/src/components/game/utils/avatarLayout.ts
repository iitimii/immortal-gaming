export interface Point {
  x: number
  y: number
}

interface PositionedObject {
  id: string
  x: number
  y: number
}

/**
 * Compute visual offsets for avatars within a tile so they do not overlap
 * @param items Objects with coordinates
 * @param radius Offset radius as a fraction of tile size (0.25 = a quarter tile)
 */
export function calculateVisualOffsets<T extends PositionedObject>(
  items: T[],
  radius: number = 0.25
): Map<string, Point> {
  const groups = new Map<string, T[]>()
  const offsets = new Map<string, Point>()

  // 1. Group by coordinate
  for (const item of items) {
    const key = `${item.x},${item.y}`
    if (!groups.has(key)) {
      groups.set(key, [])
    }
    groups.get(key)!.push(item)
  }

  // 2. Compute offsets per group
  for (const group of groups.values()) {
    const count = group.length
    
    // A single avatar needs no offset; center it
    if (count <= 1) {
      offsets.set(group[0].id, { x: 0, y: 0 })
      continue
    }

    // Multiple avatars are arranged in a circle
    // evenly spaced around it regardless of count
    // starting at -PI/2 (straight up) for a more intuitive layout
    const angleStep = (Math.PI * 2) / count
    
    group.forEach((item, index) => {
      const angle = index * angleStep - Math.PI / 2
      offsets.set(item.id, {
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius
      })
    })
  }

  return offsets
}

