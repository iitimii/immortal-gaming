/**
 * Theme and style helpers.
 * Centralizes color mapping and rarity detection.
 */

import type { EffectEntity } from '../types/core';

// Rarity color mapping
export const GRADE_COLORS: Record<string, string> = {
  'SR': '#c488fd', // Purple
  'Upper': '#c488fd',
  
  'R': '#88fdc4', // Green-ish
  'Middle': '#88fdc4',
  
  'SSR': '#fddc88', // Gold
  'Artifact': '#fddc88',
  
  'Default': '#cccccc',
};

export type EntityGradeTone = 'default' | 'epic' | 'legendary';

export function getEntityGradeTone(grade?: string | null): EntityGradeTone {
  const value = String(grade || '').toUpperCase();
  if (!value) return 'default';
  if (value.includes('SSR') || value.includes('ARTIFACT')) {
    return 'legendary';
  }
  if (value.includes('SR') || value.includes('UPPER')) {
    return 'epic';
  }
  return 'default';
}

/**
 * Resolve an entity's display color.
 * Prefers the entity's own `color`, then falls back to its grade/rarity.
 */
export function getEntityColor(entity: Partial<EffectEntity> | undefined | null): string | undefined {
  if (!entity) return undefined;

  // 1. Explicit color (RGB array)
  if (entity.color && Array.isArray(entity.color) && entity.color.length === 3) {
    const [r, g, b] = entity.color;
    return `rgb(${r},${g},${b})`;
  }
  
  // 2. Explicit color (string)
  if (typeof entity.color === 'string') {
    return entity.color;
  }

  // 3. Map by rarity/grade
  const grade = entity.grade || entity.rarity;
  if (!grade) return undefined;
  
  // Simple substring match
  for (const [key, color] of Object.entries(GRADE_COLORS)) {
    if (grade.includes(key)) return color;
  }

  return undefined;
}

