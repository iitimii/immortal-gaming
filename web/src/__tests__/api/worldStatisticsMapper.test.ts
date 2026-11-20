import { describe, expect, it } from 'vitest'
import { createEmptyWorldStatistics, normalizeWorldStatistics } from '@/api/mappers/worldStatistics'
import type { WorldStatisticsResponseDTO } from '@/types/api'

const dto: WorldStatisticsResponseDTO = {
  living_count: 4,
  realms: [
    {
      id: 'QI_REFINEMENT',
      label: 'Qi Refinement',
      count: 3,
      stages: [
        { id: 'EARLY_STAGE', label: 'Early Stage', count: 2 },
        { id: 'MIDDLE_STAGE', label: 'Middle Stage', count: 1 },
        { id: 'LATE_STAGE', label: 'Late Stage', count: 0 },
      ],
    },
    {
      id: 'FOUNDATION_ESTABLISHMENT',
      label: 'Foundation Establishment',
      count: 1,
      stages: [
        { id: 'EARLY_STAGE', label: 'Early Stage', count: 1 },
        { id: 'MIDDLE_STAGE', label: 'Middle Stage', count: 0 },
        { id: 'LATE_STAGE', label: 'Late Stage', count: 0 },
      ],
    },
  ],
  distributions: {
    sect: [
      { id: '1', label: 'High Heaven Sword Sect', count: 3 },
      { id: 'rogue', label: 'Rogue Cultivator', count: 1 },
    ],
    race: [{ id: 'human', label: 'Human', count: 4 }],
    alignment: [],
    gender: [
      { id: 'male', label: 'Male', count: 3 },
      { id: 'female', label: 'Female', count: 1 },
    ],
    orthodoxy: [{ id: 'dao', label: 'Dao', count: 4 }],
  },
  age: { average: 52.5, oldest: { id: 'a1', name: 'Elder', value: 120 } },
  wealth: { total: 300, average: 75, richest: { id: 'a2', name: 'Merchant', value: 200 } },
  deceased: {
    total: 3,
    top_reasons: [
      { id: 'battle', label: 'Killed in battle', count: 2 },
      { id: 'old_age', label: 'Died of old age', count: 1 },
    ],
  },
}

describe('normalizeWorldStatistics', () => {
  it('maps the DTO to camelCase and computes percentages', () => {
    const stats = normalizeWorldStatistics(dto)

    expect(stats.livingCount).toBe(4)
    expect(stats.realms[0]).toMatchObject({ id: 'QI_REFINEMENT', count: 3, percent: 75 })
    // Stage percentages are relative to their realm.
    expect(stats.realms[0].stages.map((stage) => stage.percent)).toEqual([66.7, 33.3, 0])
    expect(stats.distributions.sect).toEqual([
      { id: '1', label: 'High Heaven Sword Sect', count: 3, percent: 75 },
      { id: 'rogue', label: 'Rogue Cultivator', count: 1, percent: 25 },
    ])
    expect(stats.distributions.alignment).toEqual([])
    expect(stats.age).toEqual({ average: 52.5, oldest: { id: 'a1', name: 'Elder', value: 120 } })
    expect(stats.wealth.richest).toEqual({ id: 'a2', name: 'Merchant', value: 200 })
    expect(stats.deceased.total).toBe(3)
    expect(stats.deceased.topReasons.map((item) => item.percent)).toEqual([66.7, 33.3])
  })

  it('falls back to empty statistics for missing data', () => {
    expect(normalizeWorldStatistics(undefined)).toEqual(createEmptyWorldStatistics())
    expect(normalizeWorldStatistics({ living_count: 0, age: { average: 0, oldest: null } } as never))
      .toEqual(createEmptyWorldStatistics())
  })
})
