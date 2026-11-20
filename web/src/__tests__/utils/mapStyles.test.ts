import { describe, it, expect } from 'vitest'
import {
  getRegionTextMetrics,
  getRegionTextStyle,
} from '@/utils/mapStyles'

describe('mapStyles', () => {
  describe('getRegionTextMetrics', () => {
    it('should return metrics per region type', () => {
      expect(getRegionTextMetrics('sect')).toEqual({
        fontSize: 64,
        lineHeight: 70,
        strokeWidth: 4
      })
      expect(getRegionTextMetrics('city')).toEqual({
        fontSize: 70,
        lineHeight: 77,
        strokeWidth: 4
      })
      expect(getRegionTextMetrics('unknown')).toEqual({
        fontSize: 68,
        lineHeight: 75,
        strokeWidth: 4
      })
    })
  })

  describe('getRegionTextStyle', () => {
    it('should return sect style for sect labels', () => {
      const style = getRegionTextStyle('sect')
      expect(style.fontFamily).toBe('"Microsoft YaHei", sans-serif')
      expect(style.fontSize).toBe(64)
      expect(style.lineHeight).toBe(70)
      expect(style.fill).toBe('#ffcc00')
      expect(style.dropShadow).toBeDefined()
      expect(style.stroke).toEqual({
        color: '#000000',
        width: 4,
        join: 'round'
      })
    })

    it('should return city style for city type', () => {
      const style = getRegionTextStyle('city')
      expect(style.fill).toBe('#ccffcc')
      expect(style.fontSize).toBe(70)
      expect(style.lineHeight).toBe(77)
      expect(style.dropShadow).toEqual({
        color: '#000000',
        blur: 2,
        angle: Math.PI / 6,
        distance: 2,
        alpha: 0.8
      })
    })

    it('should return default style for unknown or empty type', () => {
      expect(getRegionTextStyle('unknown').fill).toBe('#ffffff')
      expect(getRegionTextStyle('').fill).toBe('#ffffff')
    })
  })
})
