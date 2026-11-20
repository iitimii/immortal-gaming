import { describe, expect, it } from 'vitest';
import {
  buildVisibleRegionLabels,
  estimateRegionLabelSize,
  formatRegionDisplayName
} from '@/components/game/utils/mapLabels';
import type { RegionSummary } from '@/types/core';

function createRegion(overrides: Partial<RegionSummary>): RegionSummary {
  return {
    id: String(overrides.id ?? '1'),
    name: overrides.name ?? 'Test Region',
    type: overrides.type ?? 'normal',
    x: overrides.x ?? 0,
    y: overrides.y ?? 0,
    sect_id: overrides.sect_id,
    sect_name: overrides.sect_name,
    sect_color: overrides.sect_color,
    sect_is_active: overrides.sect_is_active,
    sub_type: overrides.sub_type
  };
}

describe('mapLabels', () => {
  it('wraps English map labels into at most two lines', () => {
    expect(formatRegionDisplayName('Purple Bamboo Secluded Realm')).toBe(
      'Purple Bamboo\nSecluded Realm'
    );
  });

  it('keeps short labels on a single line and truncates long single words', () => {
    expect(formatRegionDisplayName('Qingyun City')).toBe('Qingyun City');
    expect(formatRegionDisplayName('Supercalifragilisticexpialidocious')).toBe('Supercalifragil…');
  });

  it('estimates label hit size from rendered map text metrics', () => {
    const singleLineSize = estimateRegionLabelSize('Qingyun City', 'normal');
    const latinSize = estimateRegionLabelSize('Purple Bamboo\nSecluded Realm', 'normal');

    expect(singleLineSize.width).toBeGreaterThan(450);
    expect(singleLineSize.height).toBeGreaterThan(70);
    expect(latinSize.width).toBeGreaterThan(300);
    expect(latinSize.height).toBeGreaterThan(140);
  });

  it('avoids overlaps by moving lower-priority labels', () => {
    const labels = buildVisibleRegionLabels(
      [
        createRegion({ id: 'normal', type: 'normal', name: 'Purple Bamboo Secluded Realm', x: 10, y: 10 }),
        createRegion({ id: 'city', type: 'city', name: 'Qingyun City', x: 10, y: 10 })
      ]
    );

    expect(labels).toHaveLength(2);
    expect(labels.map((label) => label.id)).toEqual(['city', 'normal']);
    expect(labels[0]?.labelX).toBe((10 * 64) + (64 / 2));
    expect(labels[0]?.labelY).toBe((10 * 64) + (64 * 1.5));
    expect(
      labels[1]?.labelX !== labels[0]?.labelX || labels[1]?.labelY !== labels[0]?.labelY
    ).toBe(true);
  });

  it('keeps separated labels visible', () => {
    const labels = buildVisibleRegionLabels(
      [
        createRegion({ id: 'a', type: 'city', name: 'Qingyun City', x: 2, y: 2 }),
        createRegion({ id: 'b', type: 'sect', name: 'Echo Valley', x: 12, y: 8 })
      ]
    );

    expect(labels.map((label) => label.id)).toEqual(['a', 'b']);
  });

  it('moves long English labels before allowing overlap', () => {
    const labels = buildVisibleRegionLabels(
      [
        createRegion({ id: '414', type: 'sect', name: 'Asura Blood Pool', x: 10, y: 22 }),
        createRegion({ id: '102', type: 'normal', name: 'Western Quicksand', x: 4, y: 23 })
      ]
    );

    expect(labels.map((label) => label.id)).toEqual(['414', '102']);
    expect(labels[1]?.labelX).toBe((4 * 64) + (64 / 2));
    expect(labels[1]?.labelY).not.toBe((23 * 64) + (64 * 1.5));
  });

  it('avoids overlap for labels anchored on the same tile', () => {
    const labels = buildVisibleRegionLabels(
      [
        createRegion({ id: 'a', type: 'sect', name: 'Asura Blood Pool', x: 10, y: 22 }),
        createRegion({ id: 'b', type: 'normal', name: 'Western Quicksand', x: 10, y: 22 })
      ]
    );

    expect(labels).toHaveLength(2);
    expect(labels.map((label) => label.id)).toEqual(['a', 'b']);
    expect(
      labels[1]?.labelX !== labels[0]?.labelX || labels[1]?.labelY !== labels[0]?.labelY
    ).toBe(true);
  });
});
