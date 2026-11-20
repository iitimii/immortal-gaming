import type {
  AvatarCompareItemDTO,
  AvatarCompareLabelDTO,
  AvatarCompareRelationDTO,
  AvatarCompareResponseDTO,
  AvatarCompareSideDTO,
} from '@/types/api'
import type {
  AvatarCompareItem,
  AvatarCompareLabel,
  AvatarCompareRelation,
  AvatarCompareSide,
  AvatarComparison,
} from '@/types/core'

function toNumber(value: unknown, fallback = 0): number {
  const num = Number(value)
  return Number.isFinite(num) ? num : fallback
}

function clampProbability(value: unknown): number {
  return Math.min(1, Math.max(0, toNumber(value, 0.5)))
}

function normalizeLabel(input: AvatarCompareLabelDTO | null | undefined): AvatarCompareLabel | null {
  if (!input || input.id === undefined || input.id === null) return null
  return { id: String(input.id), label: input.label ?? '' }
}

function requireLabel(input: AvatarCompareLabelDTO | null | undefined): AvatarCompareLabel {
  return normalizeLabel(input) ?? { id: '', label: '' }
}

function normalizeItem(input: AvatarCompareItemDTO | null | undefined): AvatarCompareItem | null {
  if (!input || !input.id) return null
  return {
    id: String(input.id),
    name: input.name ?? '',
    grade: input.grade ?? '',
    gradeRank: toNumber(input.grade_rank),
    attribute: input.attribute ?? '',
  }
}

function normalizeSide(input: Partial<AvatarCompareSideDTO> | null | undefined): AvatarCompareSide {
  return {
    id: String(input?.id ?? ''),
    name: input?.name ?? '',
    nickname: input?.nickname || null,
    realm: requireLabel(input?.realm),
    stage: requireLabel(input?.stage),
    cultivationDisplay: input?.cultivation_display ?? '',
    level: toNumber(input?.level),
    age: toNumber(input?.age),
    lifespan: toNumber(input?.lifespan),
    hp: { cur: toNumber(input?.hp?.cur), max: toNumber(input?.hp?.max) },
    battleStrength: toNumber(input?.battle_strength),
    root: requireLabel(input?.root),
    orthodoxy: normalizeLabel(input?.orthodoxy),
    alignment: normalizeLabel(input?.alignment),
    sect: input?.sect
      ? { id: String(input.sect.id), name: input.sect.name ?? '', rank: input.sect.rank ?? '' }
      : null,
    technique: normalizeItem(input?.technique),
    weapon: normalizeItem(input?.weapon),
    auxiliary: normalizeItem(input?.auxiliary),
    spiritStones: toNumber(input?.spirit_stones),
    relationCount: toNumber(input?.relation_count),
  }
}

function normalizeRelation(input: Partial<AvatarCompareRelationDTO> | null | undefined): AvatarCompareRelation {
  return {
    labels: Array.isArray(input?.labels) ? input.labels.map(String) : [],
    numericRelation: input?.numeric_relation ?? 'stranger',
    friendliness: toNumber(input?.friendliness),
  }
}

export function normalizeAvatarComparison(
  input: Partial<AvatarCompareResponseDTO> | null | undefined,
): AvatarComparison {
  const aWin = clampProbability(input?.battle?.a_win_probability)
  const bWinRaw = input?.battle?.b_win_probability
  return {
    a: normalizeSide(input?.a),
    b: normalizeSide(input?.b),
    relation: {
      aToB: normalizeRelation(input?.relation?.a_to_b),
      bToA: normalizeRelation(input?.relation?.b_to_a),
    },
    battle: {
      aStrength: toNumber(input?.battle?.a_strength),
      bStrength: toNumber(input?.battle?.b_strength),
      aWinProbability: aWin,
      bWinProbability: bWinRaw === undefined || bWinRaw === null ? 1 - aWin : clampProbability(bWinRaw),
      method: input?.battle?.method ?? '',
    },
  }
}
