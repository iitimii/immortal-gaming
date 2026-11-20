/**
 * Formatting utilities
 */


export function formatHp(current: number, max: number): string {
  return `${Math.floor(current)} / ${max}`;
}

export function formatAge(age: number, lifespan: number): string {
  return `${age} / ${lifespan}`;
}

