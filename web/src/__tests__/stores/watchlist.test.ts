import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { nextTick } from 'vue'

const { fetchDeceasedList } = vi.hoisted(() => ({
  fetchDeceasedList: vi.fn(),
}))

vi.mock('@/api/modules/world', () => ({
  worldApi: { fetchDeceasedList },
}))

import { useWatchlistStore, watchlistStorageKey } from '@/stores/watchlist'
import { useWorldStore } from '@/stores/world'
import { useAvatarStore } from '@/stores/avatar'
import type { WorldStateSnapshot } from '@/api/mappers/world'
import type { AvatarSummary } from '@/types/core'

class MemoryStorage {
  data = new Map<string, string>()
  getItem(key: string) {
    return this.data.has(key) ? this.data.get(key)! : null
  }
  setItem(key: string, value: string) {
    this.data.set(key, String(value))
  }
  removeItem(key: string) {
    this.data.delete(key)
  }
  clear() {
    this.data.clear()
  }
}

let storage: MemoryStorage
const originalDescriptor = Object.getOwnPropertyDescriptor(window, 'localStorage')

function installStorage(value: unknown) {
  Object.defineProperty(window, 'localStorage', { configurable: true, get: () => value })
}

function avatar(id: string, extra: Partial<AvatarSummary> = {}): AvatarSummary {
  return { id, name: `Name ${id}`, x: 0, y: 0, cultivation_display: 'Qi Refinement Early', ...extra }
}

function snapshot(playthroughId: string, avatars: AvatarSummary[]): WorldStateSnapshot {
  return {
    status: 'ok',
    year: 100,
    month: 1,
    avatars,
    events: [],
    phenomenon: null,
    activeDomains: [],
    worldRevision: 1,
    playthroughId,
  }
}

async function settle() {
  for (let i = 0; i < 5; i += 1) {
    await Promise.resolve()
    await nextTick()
  }
}

/** Mirrors worldStore.applyStateSnapshot: run id + complete avatar list in one tick. */
function loadRun(playthroughId: string, avatars: AvatarSummary[]) {
  useWorldStore().playthroughId = playthroughId
  useAvatarStore().setAvatarsFromState(snapshot(playthroughId, avatars))
  useWorldStore().isLoaded = true
}

function stored(scope: string) {
  const raw = storage.getItem(watchlistStorageKey(scope))
  return raw ? JSON.parse(raw) : null
}

describe('watchlist store', () => {
  beforeEach(() => {
    storage = new MemoryStorage()
    installStorage(storage)
    fetchDeceasedList.mockReset()
    fetchDeceasedList.mockResolvedValue([])
  })

  afterEach(() => {
    if (originalDescriptor) {
      Object.defineProperty(window, 'localStorage', originalDescriptor)
    }
  })

  it('toggles avatars and persists them under the current run', async () => {
    loadRun('run-a', [avatar('a1'), avatar('a2')])
    const store = useWatchlistStore()
    await settle()

    store.toggle('a1')
    store.toggle('a2')
    expect(store.isWatched('a1')).toBe(true)
    expect(store.watchedIds).toEqual(['a1', 'a2'])
    expect(stored('run-a').entries.map((e: { id: string }) => e.id)).toEqual(['a1', 'a2'])
    expect(stored('run-a').entries[0]).toMatchObject({ name: 'Name a1', realm: 'Qi Refinement Early', deceased: false })

    store.toggle('a1')
    expect(store.isWatched('a1')).toBe(false)
    expect(stored('run-a').entries.map((e: { id: string }) => e.id)).toEqual(['a2'])
  })

  it('restores the saved list when the same run is loaded again', async () => {
    storage.setItem(
      watchlistStorageKey('run-a'),
      JSON.stringify({ version: 1, entries: [{ id: 'a2', name: 'Bob', realm: 'Core', deceased: false }] }),
    )
    const store = useWatchlistStore()
    loadRun('run-a', [avatar('a2')])
    await settle()

    expect(store.scopeId).toBe('run-a')
    expect(store.watchedIds).toEqual(['a2'])
  })

  it('keeps watchlists of different runs apart', async () => {
    const store = useWatchlistStore()
    loadRun('run-a', [avatar('a1')])
    await settle()
    store.toggle('a1')

    loadRun('run-b', [avatar('b1')])
    await settle()
    expect(store.scopeId).toBe('run-b')
    expect(store.watchedIds).toEqual([])
    store.toggle('b1')

    loadRun('run-a', [avatar('a1')])
    await settle()
    expect(store.watchedIds).toEqual(['a1'])
    expect(stored('run-b').entries.map((e: { id: string }) => e.id)).toEqual(['b1'])
  })

  it('falls back to an in-memory list without a run id', async () => {
    const store = useWatchlistStore()
    loadRun('', [avatar('a1')])
    await settle()

    store.toggle('a1')
    expect(store.isWatched('a1')).toBe(true)
    expect(storage.data.size).toBe(0)

    useWorldStore().reset()
    await settle()
    expect(store.watchedIds).toEqual([])
  })

  it('degrades gracefully when storage throws', async () => {
    const throwing = {
      getItem: vi.fn(() => { throw new Error('denied') }),
      setItem: vi.fn(() => { throw new Error('quota') }),
    }
    installStorage(throwing)
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})

    const store = useWatchlistStore()
    loadRun('run-a', [avatar('a1')])
    await settle()

    expect(store.watchedIds).toEqual([])
    store.toggle('a1')
    expect(store.isWatched('a1')).toBe(true)
    expect(throwing.setItem).toHaveBeenCalled()
    expect(warn).toHaveBeenCalled()
  })

  it('degrades gracefully when the storage accessor itself throws', async () => {
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      get: () => { throw new Error('SecurityError') },
    })
    vi.spyOn(console, 'warn').mockImplementation(() => {})

    const store = useWatchlistStore()
    loadRun('run-a', [avatar('a1')])
    await settle()

    store.toggle('a1')
    expect(store.isWatched('a1')).toBe(true)
  })

  it('ignores corrupt stored data', async () => {
    storage.setItem(watchlistStorageKey('run-a'), '{not json')
    const store = useWatchlistStore()
    loadRun('run-a', [avatar('a1')])
    await settle()

    expect(store.watchedIds).toEqual([])
  })

  it('keeps dead watched avatars marked deceased and prunes deleted ones on a full snapshot', async () => {
    storage.setItem(
      watchlistStorageKey('run-a'),
      JSON.stringify({
        version: 1,
        entries: [
          { id: 'alive', name: 'Alive', realm: 'Core', deceased: false },
          { id: 'dead', name: 'Dead', realm: 'Core', deceased: false },
          { id: 'gone', name: 'Gone', realm: 'Core', deceased: false },
        ],
      }),
    )
    fetchDeceasedList.mockResolvedValue([
      { id: 'dead', name: 'Dead One', realm_at_death: 'Nascent Soul', stage_at_death: 'Late' },
    ])

    const store = useWatchlistStore()
    loadRun('run-a', [avatar('alive')])
    await settle()

    expect(fetchDeceasedList).toHaveBeenCalledTimes(1)
    expect(store.watchedIds).toEqual(['alive', 'dead'])
    expect(store.entries[1]).toEqual({ id: 'dead', name: 'Dead One', realm: 'Nascent Soul Late', deceased: true })
    expect(stored('run-a').entries.map((e: { id: string }) => e.id)).toEqual(['alive', 'dead'])
  })

  it('does not prune anything when the deceased archive cannot be fetched', async () => {
    storage.setItem(
      watchlistStorageKey('run-a'),
      JSON.stringify({ version: 1, entries: [{ id: 'gone', name: 'Gone', realm: '', deceased: false }] }),
    )
    fetchDeceasedList.mockRejectedValue(new Error('offline'))
    vi.spyOn(console, 'warn').mockImplementation(() => {})

    const store = useWatchlistStore()
    loadRun('run-a', [])
    await settle()

    expect(store.watchedIds).toEqual(['gone'])
  })

  it('does not prune on partial avatar deltas', async () => {
    const avatars = useAvatarStore()
    const store = useWatchlistStore()
    loadRun('run-a', [avatar('a1')])
    await settle()
    store.toggle('a1')
    fetchDeceasedList.mockClear()

    avatars.removeAvatar('a1')
    await settle()

    expect(fetchDeceasedList).not.toHaveBeenCalled()
    expect(store.watchedIds).toEqual(['a1'])
    expect(store.entries[0].name).toBe('Name a1')
  })

  it('refreshes stored name, realm and death from live avatar updates', async () => {
    const avatars = useAvatarStore()
    const store = useWatchlistStore()
    loadRun('run-a', [avatar('a1')])
    await settle()
    store.toggle('a1')

    avatars.updateAvatars([{ id: 'a1', cultivation_display: 'Core Formation Early', is_dead: true }])
    await settle()

    expect(store.entries[0]).toMatchObject({ realm: 'Core Formation Early', deceased: true })
    expect(stored('run-a').entries[0]).toMatchObject({ realm: 'Core Formation Early', deceased: true })
  })

  it('uses the provided snapshot for avatars not in the living list', async () => {
    const store = useWatchlistStore()
    loadRun('run-a', [])
    await settle()

    store.toggle('ghost', { name: 'Old Master', realm: 'Core', deceased: true })
    expect(store.entries[0]).toEqual({ id: 'ghost', name: 'Old Master', realm: 'Core', deceased: true })
  })
})
