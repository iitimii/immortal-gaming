import type { TextStyleOptions } from 'pixi.js';

type RegionTextMetrics = {
  fontSize: number;
  lineHeight: number;
  strokeWidth: number;
};

const REGION_FONT_SIZE = {
  sect: 64,
  city: 70,
  default: 68
} as const;

export function getRegionTextMetrics(type: string): RegionTextMetrics {
  const fontSize = REGION_FONT_SIZE[type as keyof typeof REGION_FONT_SIZE] ?? REGION_FONT_SIZE.default;

  return {
    fontSize,
    lineHeight: Math.round(fontSize * 1.1),
    strokeWidth: 4
  };
}

// Text styles for map region labels.
export function getRegionTextStyle(type: string): Partial<TextStyleOptions> {
  const metrics = getRegionTextMetrics(type);

  const styleByType: Record<string, Partial<TextStyleOptions>> = {
    sect: {
      fill: '#ffcc00'
    },
    city: {
      fill: '#ccffcc'
    },
    default: {
      fill: '#ffffff'
    }
  };

  return {
    fontFamily: '"Microsoft YaHei", sans-serif',
    fontSize: metrics.fontSize,
    lineHeight: metrics.lineHeight,
    fill: (styleByType[type] || styleByType.default).fill,
    stroke: { color: '#000000', width: metrics.strokeWidth, join: 'round' },
    align: 'center',
    whiteSpace: 'pre',
    dropShadow: {
      color: '#000000',
      blur: 2,
      angle: Math.PI / 6,
      distance: 2,
      alpha: 0.8
    }
  };
}
