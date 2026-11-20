import { httpClient } from '../http'
import type { WorldMilestonesResponseDTO } from '../../types/api'
import { mapWorldMilestones } from '../mappers/milestone'

export const milestoneApi = {
  async fetchWorldMilestones() {
    const data = await httpClient.get<WorldMilestonesResponseDTO>('/api/v1/query/world/milestones')
    return mapWorldMilestones(data)
  },
}
