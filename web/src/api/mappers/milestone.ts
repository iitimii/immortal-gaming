import type {
  WorldMilestoneAchievedDTO,
  WorldMilestonePendingDTO,
  WorldMilestonesResponseDTO,
} from '@/types/api'

export interface MilestoneAvatarView {
  id: string
  name: string
  clickable: boolean
  isDead: boolean
}

export interface MilestoneSectView {
  id: number
  name: string
}

export interface AchievedMilestoneView {
  key: string
  kind: string
  title: string
  description: string
  monthStamp: number
  year: number
  month: number
  dateText: string
  avatars: MilestoneAvatarView[]
  sects: MilestoneSectView[]
}

export interface PendingMilestoneView {
  key: string
  kind: string
  title: string
  description: string
}

export interface WorldMilestonesView {
  achieved: AchievedMilestoneView[]
  pending: PendingMilestoneView[]
  total: number
  openedDateText: string
}

function mapAchieved(dto: WorldMilestoneAchievedDTO): AchievedMilestoneView {
  return {
    key: dto.key,
    kind: dto.kind,
    title: dto.title,
    description: dto.description,
    monthStamp: dto.month_stamp,
    year: dto.year,
    month: dto.month,
    dateText: dto.date_text,
    avatars: (dto.avatars ?? []).map((avatar) => ({
      id: avatar.id,
      name: avatar.name,
      clickable: Boolean(avatar.available),
      isDead: Boolean(avatar.is_dead),
    })),
    sects: (dto.sects ?? []).map((sect) => ({ id: sect.id, name: sect.name })),
  }
}

function mapPending(dto: WorldMilestonePendingDTO): PendingMilestoneView {
  return {
    key: dto.key,
    kind: dto.kind,
    title: dto.title,
    description: dto.description,
  }
}

export function mapWorldMilestones(
  dto: Partial<WorldMilestonesResponseDTO> | null | undefined,
): WorldMilestonesView {
  const achieved = Array.isArray(dto?.achieved) ? dto.achieved.map(mapAchieved) : []
  // The backend already returns chronological order; a stable sort keeps that guarantee client-side.
  achieved.sort((a, b) => a.monthStamp - b.monthStamp)
  const pending = Array.isArray(dto?.pending) ? dto.pending.map(mapPending) : []
  return {
    achieved,
    pending,
    total: typeof dto?.total === 'number' ? dto.total : achieved.length + pending.length,
    openedDateText: dto?.opened_date_text ?? '',
  }
}
