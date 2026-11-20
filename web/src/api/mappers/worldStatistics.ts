import type {
  WorldStatisticsAvatarRefDTO,
  WorldStatisticsBucketDTO,
  WorldStatisticsRealmDTO,
  WorldStatisticsResponseDTO,
} from '@/types/api'
import type {
  WorldStatistics,
  WorldStatisticsAvatarRef,
  WorldStatisticsBucket,
  WorldStatisticsDistributionKey,
  WorldStatisticsRealm,
} from '@/types/core'

const DISTRIBUTION_KEYS: WorldStatisticsDistributionKey[] = ['sect', 'race', 'alignment', 'gender', 'orthodoxy']

function toPercent(count: number, total: number): number {
  if (total <= 0) return 0
  return Math.round((count / total) * 1000) / 10
}

function normalizeBuckets(
  input: WorldStatisticsBucketDTO[] | undefined,
  total?: number,
): WorldStatisticsBucket[] {
  if (!Array.isArray(input)) return []
  const items = input.map((item) => ({
    id: String(item.id ?? ''),
    label: item.label ?? '',
    count: Number(item.count ?? 0),
  }))
  const base = total ?? items.reduce((sum, item) => sum + item.count, 0)
  return items.map((item) => ({ ...item, percent: toPercent(item.count, base) }))
}

function normalizeRealms(input: WorldStatisticsRealmDTO[] | undefined, total: number): WorldStatisticsRealm[] {
  if (!Array.isArray(input)) return []
  return input.map((realm) => {
    const count = Number(realm.count ?? 0)
    return {
      id: String(realm.id ?? ''),
      label: realm.label ?? '',
      count,
      percent: toPercent(count, total),
      stages: normalizeBuckets(realm.stages, count),
    }
  })
}

function normalizeAvatarRef(input: WorldStatisticsAvatarRefDTO | null | undefined): WorldStatisticsAvatarRef | null {
  if (!input || !input.id) return null
  return {
    id: String(input.id),
    name: input.name ?? '',
    value: Number(input.value ?? 0),
  }
}

export function createEmptyWorldStatistics(): WorldStatistics {
  return {
    livingCount: 0,
    realms: [],
    distributions: { sect: [], race: [], alignment: [], gender: [], orthodoxy: [] },
    age: { average: 0, oldest: null },
    wealth: { total: 0, average: 0, richest: null },
    deceased: { total: 0, topReasons: [] },
  }
}

export function normalizeWorldStatistics(
  input: Partial<WorldStatisticsResponseDTO> | null | undefined,
): WorldStatistics {
  const livingCount = Number(input?.living_count ?? 0)
  const distributions = createEmptyWorldStatistics().distributions
  for (const key of DISTRIBUTION_KEYS) {
    distributions[key] = normalizeBuckets(input?.distributions?.[key], livingCount)
  }
  const deceasedTotal = Number(input?.deceased?.total ?? 0)

  return {
    livingCount,
    realms: normalizeRealms(input?.realms, livingCount),
    distributions,
    age: {
      average: Number(input?.age?.average ?? 0),
      oldest: normalizeAvatarRef(input?.age?.oldest),
    },
    wealth: {
      total: Number(input?.wealth?.total ?? 0),
      average: Number(input?.wealth?.average ?? 0),
      richest: normalizeAvatarRef(input?.wealth?.richest),
    },
    deceased: {
      total: deceasedTotal,
      topReasons: normalizeBuckets(input?.deceased?.top_reasons, deceasedTotal),
    },
  }
}
