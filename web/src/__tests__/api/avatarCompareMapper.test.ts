import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AvatarCompareResponseDTO } from '@/types/api'

const getMock = vi.fn()

vi.mock('@/api/http', () => ({
  httpClient: {
    get: getMock,
    post: vi.fn(),
    delete: vi.fn(),
  },
}))

import { normalizeAvatarComparison } from '@/api/mappers/avatarCompare'
import { makeCompareDTO } from '../fixtures/avatarCompare'

describe('normalizeAvatarComparison', () => {
  beforeEach(() => {
    getMock.mockReset()
  })

  it('maps the snake_case DTO to camelCase domain objects', () => {
    const result = normalizeAvatarComparison(makeCompareDTO())

    expect(result.a.cultivationDisplay).toBe('Core Formation Late Stage')
    expect(result.a.battleStrength).toBe(35)
    expect(result.a.spiritStones).toBe(300)
    expect(result.a.relationCount).toBe(3)
    expect(result.a.nickname).toBe('Azure Sword')
    expect(result.a.technique).toEqual({ id: '7', name: 'Cloud Palm', grade: 'Upper', gradeRank: 2, attribute: 'Metal' })
    expect(result.a.auxiliary).toBeNull()
    expect(result.a.sect).toEqual({ id: '1', name: 'Azure Cloud Sect', rank: 'Elder' })
    expect(result.b.sect).toBeNull()
    expect(result.b.weapon).toBeNull()
    expect(result.b.auxiliary?.gradeRank).toBe(0)
    expect(result.b.nickname).toBeNull()
    expect(result.relation.aToB).toEqual({ labels: ['Sworn Brother', 'Friend'], numericRelation: 'friend', friendliness: 60 })
    expect(result.battle).toEqual({
      aStrength: 35,
      bStrength: 10,
      aWinProbability: 0.977,
      bWinProbability: 0.023,
      method: 'closed_form',
    })
  })

  it('fills safe defaults for missing or malformed fields', () => {
    const result = normalizeAvatarComparison({
      battle: { a_win_probability: 1.7 } as AvatarCompareResponseDTO['battle'],
    })

    expect(result.a.id).toBe('')
    expect(result.a.realm).toEqual({ id: '', label: '' })
    expect(result.a.orthodoxy).toBeNull()
    expect(result.a.hp).toEqual({ cur: 0, max: 0 })
    expect(result.relation.bToA).toEqual({ labels: [], numericRelation: 'stranger', friendliness: 0 })
    expect(result.battle.aWinProbability).toBe(1)
    expect(result.battle.bWinProbability).toBe(0)
  })

  it('avatarApi.fetchAvatarComparison queries the v1 compare endpoint', async () => {
    const { avatarApi } = await import('@/api/modules/avatar')
    getMock.mockResolvedValue(makeCompareDTO())

    const result = await avatarApi.fetchAvatarComparison('a1', 'b 2')

    expect(getMock).toHaveBeenCalledWith('/api/v1/query/avatars/compare?a=a1&b=b+2')
    expect(result.a.name).toBe('Elder Lan')
    expect(result.battle.aWinProbability).toBe(0.977)
  })
})
