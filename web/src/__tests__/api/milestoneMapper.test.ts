import { beforeEach, describe, expect, it, vi } from 'vitest'

import { mapWorldMilestones } from '@/api/mappers/milestone'
import type { WorldMilestonesResponseDTO } from '@/types/api'

const getMock = vi.hoisted(() => vi.fn())

vi.mock('@/api/http', () => ({
  httpClient: {
    get: getMock,
  },
}))

const dto: WorldMilestonesResponseDTO = {
  achieved: [
    {
      key: 'first_sect_war',
      kind: 'sect_war',
      title: 'First Sect War',
      description: 'A and B went to war.',
      month_stamp: 30,
      year: 2,
      month: 7,
      date_text: 'Year 2 Month 7',
      avatars: [],
      sects: [{ id: 1, name: 'A' }, { id: 2, name: 'B' }],
    },
    {
      key: 'first_realm_foundation_establishment',
      kind: 'realm',
      title: 'First to Reach Foundation Establishment',
      description: 'Hero broke through.',
      month_stamp: 14,
      year: 1,
      month: 3,
      date_text: 'Year 1 Month 3',
      avatars: [
        { id: 'a-1', name: 'Hero', available: true, is_dead: false },
        { id: 'a-2', name: 'Gone', available: false, is_dead: true },
      ],
      sects: [],
    },
  ],
  pending: [
    { key: 'first_age_100', kind: 'age', title: 'First to Live 100 Years', description: 'Live long.' },
  ],
  total: 3,
  opened_month_stamp: 12,
  opened_date_text: 'Year 1 Month 1',
}

describe('mapWorldMilestones', () => {
  it('maps DTO fields to camelCase views in chronological order', () => {
    const view = mapWorldMilestones(dto)

    expect(view.achieved.map(item => item.key)).toEqual([
      'first_realm_foundation_establishment',
      'first_sect_war',
    ])
    expect(view.achieved[0]).toMatchObject({
      monthStamp: 14,
      dateText: 'Year 1 Month 3',
      avatars: [
        { id: 'a-1', name: 'Hero', clickable: true, isDead: false },
        { id: 'a-2', name: 'Gone', clickable: false, isDead: true },
      ],
    })
    expect(view.achieved[1].sects).toEqual([{ id: 1, name: 'A' }, { id: 2, name: 'B' }])
    expect(view.pending).toEqual([
      { key: 'first_age_100', kind: 'age', title: 'First to Live 100 Years', description: 'Live long.' },
    ])
    expect(view.total).toBe(3)
    expect(view.openedDateText).toBe('Year 1 Month 1')
  })

  it('tolerates missing payload fields', () => {
    expect(mapWorldMilestones(undefined)).toEqual({
      achieved: [],
      pending: [],
      total: 0,
      openedDateText: '',
    })
  })
})

describe('milestoneApi', () => {
  beforeEach(() => {
    getMock.mockReset()
  })

  it('fetches milestones from the public v1 query and maps them', async () => {
    const { milestoneApi } = await import('@/api/modules/milestone')
    getMock.mockResolvedValueOnce(dto)

    const view = await milestoneApi.fetchWorldMilestones()

    expect(getMock).toHaveBeenCalledWith('/api/v1/query/world/milestones')
    expect(view.achieved).toHaveLength(2)
  })
})
