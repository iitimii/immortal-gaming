import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'

import {
  formatPopulationGrowthText,
  formatPopulationRatioText,
  formatPopulationText,
  formatPopulationValue,
} from '@/utils/populationFormat'

function createTranslator() {
  const i18n = createI18n({
    legacy: false,
    locale: 'en-US',
    messages: {
      'en-US': {
        game: {
          mortal_system: {
            population_value: '{value}',
            population_growth_value: '{value}/month',
            population_ratio_value: '{current} / {capacity}',
          },
        },
      },
    },
  })

  return i18n.global.t
}

describe('populationFormat', () => {
  it('converts backend units of 10,000 into compact western units', () => {
    const t = createTranslator()

    expect(formatPopulationValue(831.1, 'en-US')).toBe('8.31M')
    expect(formatPopulationText(831.1, t, 'en-US')).toBe('8.31M')
    expect(formatPopulationGrowthText(3.23, t, 'en-US')).toBe('+32.3K/month')
    expect(formatPopulationRatioText(831.1, 955.0, t, 'en-US')).toBe('8.31M / 9.55M')
  })

  it('defaults to en-US and handles missing or negative values', () => {
    const t = createTranslator()

    expect(formatPopulationValue(undefined)).toBe('0')
    expect(formatPopulationGrowthText(-0.5, t)).toBe('-5K/month')
    expect(formatPopulationGrowthText(0, t)).toBe('0/month')
  })
})
