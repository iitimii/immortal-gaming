import { describe, expect, it } from 'vitest';
import { getItemIconUrl, hasItemIcon } from '@/utils/itemIcons';

describe('itemIcons', () => {
  it('resolves concrete item icons by inferred category and id', () => {
    expect(getItemIconUrl({ id: '1001', name: 'Qi Refining Sword', type: 'SWORD' })).toContain('weapon_1001');
    expect(getItemIconUrl({ id: '3001', name: 'Qi Breakthrough Pill', type: 'elixir' })).toContain('elixir_3001');
    expect(getItemIconUrl({ id: '1', name: 'Primordial Golden Body', type: 'technique' })).toContain('technique_1');
    expect(getItemIconUrl({ id: '1', name: 'Child of Fortune', key: 'CHILD_OF_FORTUNE', rarity: 'SSR' })).toContain('goldfinger_1');
    expect(getItemIconUrl({ id: '1', name: 'Spirit Rabbit', type: 'animal' })).toContain('animal_1');
    expect(getItemIconUrl({ id: '1', name: 'Rare Herb', type: 'plant' })).toContain('plant_1');
    expect(getItemIconUrl({ id: '1', name: 'Dark Iron Lode', type: 'lode' })).toContain('lode_1');
    expect(getItemIconUrl({ id: '1', name: 'Spirit Rabbit Fur', type: 'material' })).toContain('material_1');
  });

  it('falls back to category icons for custom content', () => {
    expect(getItemIconUrl({ id: '900001', name: 'Self-made Technique', type: 'technique', is_custom: true })).toContain('fallback_technique');
    expect(getItemIconUrl({ id: '930001', name: 'Custom Cheat', key: 'CUSTOM', rarity: 'SSR', is_custom: true })).toContain('fallback_goldfinger');
  });

  it('returns an unknown fallback for non-item entities', () => {
    expect(getItemIconUrl({ id: 'unknown', name: 'Unknown Entity' })).toContain('fallback_unknown');
    expect(hasItemIcon({ id: 'unknown', name: 'Unknown Entity' })).toBe(true);
  });
});
