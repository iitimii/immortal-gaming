import { beforeEach, describe, expect, it, vi } from 'vitest'

const getMock = vi.fn()
const postMock = vi.fn()
const deleteMock = vi.fn()

vi.mock('@/api/http', () => ({
  httpClient: {
    get: getMock,
    post: postMock,
    delete: deleteMock,
  },
}))

describe('public api module migration', () => {
  beforeEach(() => {
    getMock.mockReset()
    postMock.mockReset()
    deleteMock.mockReset()
  })

  it('worldApi fetches world state and map from /api/v1', async () => {
    const { worldApi } = await import('@/api/modules/world')
    getMock.mockResolvedValueOnce({ status: 'ok', year: 100, month: 1 })
    getMock.mockResolvedValueOnce({ data: [], regions: [], render_config: {} })

    const state = await worldApi.fetchInitialState()
    const map = await worldApi.fetchMap()

    expect(getMock).toHaveBeenNthCalledWith(1, '/api/v1/query/world/state')
    expect(getMock).toHaveBeenNthCalledWith(2, '/api/v1/query/world/map')
    expect(state.avatars).toEqual([])
    expect(state.events).toEqual([])
    expect(map.renderConfig).toEqual({ water_speed: 'high', cloud_frequency: 'none' })
  })

  it('eventApi fetches events from /api/v1 query endpoint', async () => {
    const { eventApi } = await import('@/api/modules/event')
    getMock.mockResolvedValue({ events: [], next_cursor: null, has_more: false })

    const page = await eventApi.fetchEvents({ avatar_id: 'a1', limit: 20 })

    expect(getMock).toHaveBeenCalledWith('/api/v1/query/events?avatar_id=a1&limit=20')
    expect(page).toEqual({ events: [], nextCursor: null, hasMore: false })
  })

  it('eventApi cleans up events through /api/v1 command endpoint', async () => {
    const { eventApi } = await import('@/api/modules/event')
    deleteMock.mockResolvedValue({ deleted: 12 })

    await eventApi.cleanupEvents(false, 1200)

    expect(deleteMock).toHaveBeenCalledWith('/api/v1/command/events/cleanup?keep_major=false&before_month_stamp=1200')
  })

  it('worldApi fetches sect territories from /api/v1', async () => {
    const { worldApi } = await import('@/api/modules/world')
    getMock.mockResolvedValue({ sects: [] })

    await worldApi.fetchSectTerritories()

    expect(getMock).toHaveBeenCalledWith('/api/v1/query/sects/territories')
  })

  it('worldApi fetches and normalizes world statistics from /api/v1', async () => {
    const { worldApi } = await import('@/api/modules/world')
    getMock.mockResolvedValue({ living_count: 0, deceased: { total: 1, top_reasons: [] } })

    const stats = await worldApi.fetchWorldStatistics()

    expect(getMock).toHaveBeenCalledWith('/api/v1/query/world/statistics')
    expect(stats.livingCount).toBe(0)
    expect(stats.deceased.total).toBe(1)
    expect(stats.realms).toEqual([])
  })

  it('systemApi uses /api/v1 lifecycle and save endpoints', async () => {
    const { systemApi } = await import('@/api/modules/system')
    getMock.mockResolvedValue({ status: 'idle' })
    postMock.mockResolvedValue({ status: 'ok' })

    await systemApi.fetchInitStatus()
    await systemApi.fetchSaves()
    await systemApi.saveGame('Save A')
    await systemApi.loadGame('save.json')

    expect(getMock).toHaveBeenNthCalledWith(1, '/api/v1/query/runtime/status')
    expect(getMock).toHaveBeenNthCalledWith(2, '/api/v1/query/saves')
    expect(postMock).toHaveBeenNthCalledWith(1, '/api/v1/command/game/save', { custom_name: 'Save A' })
    expect(postMock).toHaveBeenNthCalledWith(2, '/api/v1/command/game/load', { filename: 'save.json' })
  })

  it('systemApi sets simulation speed through /api/v1 command endpoint', async () => {
    const { systemApi } = await import('@/api/modules/system')
    postMock.mockResolvedValue({ status: 'ok', speed: 2, allowed_speeds: [0.5, 1, 2, 4] })

    const result = await systemApi.setSpeed(2)

    expect(postMock).toHaveBeenCalledWith('/api/v1/command/game/set-speed', { speed: 2 })
    expect(result.speed).toBe(2)
  })

  it('systemApi steps one month through /api/v1 command endpoint', async () => {
    const { systemApi } = await import('@/api/modules/system')
    postMock.mockResolvedValue({
      status: 'ok',
      year: 12,
      month: 4,
      event_count: 3,
      auto_saved: false,
      world_revision: 9,
    })

    const result = await systemApi.stepOnce()

    expect(postMock).toHaveBeenCalledWith('/api/v1/command/game/step', {})
    expect(result.month).toBe(4)
    expect(result.event_count).toBe(3)
  })

  it('systemApi startNewGame and shutdown use /api/v1 endpoints', async () => {
    const { systemApi } = await import('@/api/modules/system')
    postMock.mockResolvedValue({ status: 'ok' })

    await systemApi.startNewGame()
    await systemApi.shutdown()

    expect(postMock).toHaveBeenNthCalledWith(1, '/api/v1/command/game/reinit', {})
    expect(postMock).toHaveBeenNthCalledWith(2, '/api/v1/command/system/shutdown', {})
  })

  it('systemApi exposes pause-and-drain for edit panels', async () => {
    const { systemApi } = await import('@/api/modules/system')
    postMock.mockResolvedValue({ status: 'ok' })

    await systemApi.pauseGameAndDrain()

    expect(postMock).toHaveBeenCalledWith('/api/v1/command/game/pause-and-drain', {})
  })
})
