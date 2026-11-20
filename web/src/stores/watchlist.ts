import { defineStore } from 'pinia';
import { computed, ref, shallowRef, watch } from 'vue';
import { worldApi } from '../api/modules/world';
import type { AvatarSummary } from '../types/core';
import { logWarn } from '../utils/appError';
import { useAvatarStore } from './avatar';
import { useWorldStore } from './world';

/**
 * Per-viewer list of followed cultivators.
 *
 * It is a local preference, so it lives in browser storage keyed by the
 * backend playthrough id: saves of the same run share a watchlist, other runs
 * do not. Without a playthrough id the list is kept in memory only.
 */

export interface WatchlistEntry {
  id: string;
  /** Last known name/realm, so entries stay readable when the avatar is not loaded. */
  name: string;
  realm: string;
  deceased: boolean;
}

export type WatchlistSnapshot = Partial<Omit<WatchlistEntry, 'id'>>;

const STORAGE_PREFIX = 'cws-watchlist:';
const STORAGE_VERSION = 1;

export function watchlistStorageKey(scopeId: string): string {
  return `${STORAGE_PREFIX}${scopeId}`;
}

function readStorage(key: string): string | null {
  try {
    return window.localStorage?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string): void {
  try {
    window.localStorage?.setItem(key, value);
  } catch (e) {
    logWarn('WatchlistStore persist', e);
  }
}

function parseEntries(raw: string | null): WatchlistEntry[] {
  if (!raw) return [];
  try {
    const data = JSON.parse(raw) as { version?: number; entries?: unknown };
    if (data?.version !== STORAGE_VERSION || !Array.isArray(data.entries)) return [];
    const seen = new Set<string>();
    const result: WatchlistEntry[] = [];
    for (const item of data.entries as Array<Partial<WatchlistEntry>>) {
      if (!item || typeof item.id !== 'string' || !item.id || seen.has(item.id)) continue;
      seen.add(item.id);
      result.push({
        id: item.id,
        name: typeof item.name === 'string' ? item.name : '',
        realm: typeof item.realm === 'string' ? item.realm : '',
        deceased: item.deceased === true,
      });
    }
    return result;
  } catch {
    return [];
  }
}

function summaryRealm(avatar: AvatarSummary): string {
  return avatar.cultivation_display || avatar.realm || '';
}

export const useWatchlistStore = defineStore('watchlist', () => {
  const worldStore = useWorldStore();
  const avatarStore = useAvatarStore();

  const scopeId = ref('');
  const entries = shallowRef<WatchlistEntry[]>([]);

  const watchedIds = computed(() => entries.value.map(entry => entry.id));
  const watchedIdSet = computed(() => new Set(watchedIds.value));
  const count = computed(() => entries.value.length);

  let reconcileSeq = 0;

  function persist() {
    if (!scopeId.value) return;
    writeStorage(
      watchlistStorageKey(scopeId.value),
      JSON.stringify({ version: STORAGE_VERSION, entries: entries.value }),
    );
  }

  function commit(next: WatchlistEntry[]) {
    entries.value = next;
    persist();
  }

  function setScope(nextScopeId: string) {
    if (nextScopeId === scopeId.value) return;
    reconcileSeq++; // Drop in-flight reconciliation for the previous run.
    scopeId.value = nextScopeId;
    entries.value = nextScopeId ? parseEntries(readStorage(watchlistStorageKey(nextScopeId))) : [];
  }

  function isWatched(id: string): boolean {
    return watchedIdSet.value.has(id);
  }

  function buildEntry(id: string, snapshot?: WatchlistSnapshot): WatchlistEntry {
    const live = avatarStore.avatars.get(id);
    return {
      id,
      name: live?.name || snapshot?.name || '',
      realm: (live ? summaryRealm(live) : '') || snapshot?.realm || '',
      deceased: live ? live.is_dead === true : snapshot?.deceased === true,
    };
  }

  function add(id: string, snapshot?: WatchlistSnapshot) {
    if (!id || isWatched(id)) return;
    commit([...entries.value, buildEntry(id, snapshot)]);
  }

  function remove(id: string) {
    if (!isWatched(id)) return;
    commit(entries.value.filter(entry => entry.id !== id));
  }

  function toggle(id: string, snapshot?: WatchlistSnapshot) {
    if (isWatched(id)) {
      remove(id);
    } else {
      add(id, snapshot);
    }
  }

  function clear() {
    if (entries.value.length === 0) return;
    commit([]);
  }

  /** Refresh stored name/realm/deceased from live avatar summaries. */
  function syncFromAvatars() {
    const avatars = avatarStore.avatars;
    let changed = false;
    const next = entries.value.map(entry => {
      const live = avatars.get(entry.id);
      if (!live) return entry;
      const updated: WatchlistEntry = {
        id: entry.id,
        name: live.name || entry.name,
        realm: summaryRealm(live) || entry.realm,
        deceased: live.is_dead === true,
      };
      if (
        updated.name === entry.name &&
        updated.realm === entry.realm &&
        updated.deceased === entry.deceased
      ) {
        return entry;
      }
      changed = true;
      return updated;
    });
    if (changed) commit(next);
  }

  /**
   * Called when the avatar list is known to be complete (full world snapshot).
   * Watched ids missing from it are either dead (kept, marked deceased) or
   * gone for good (deleted / unknown to this run) and are pruned. If the
   * deceased archive cannot be fetched nothing is pruned.
   */
  async function reconcileSnapshot() {
    const seq = ++reconcileSeq;
    syncFromAvatars();
    const living = avatarStore.avatars;
    const missingIds = new Set(entries.value.filter(entry => !living.has(entry.id)).map(entry => entry.id));
    if (missingIds.size === 0) return;

    let deceased: Awaited<ReturnType<typeof worldApi.fetchDeceasedList>>;
    try {
      deceased = await worldApi.fetchDeceasedList();
    } catch (e) {
      logWarn('WatchlistStore reconcile', e);
      return;
    }
    if (seq !== reconcileSeq) return;

    const deceasedById = new Map(deceased.map(record => [record.id, record]));
    const currentLiving = avatarStore.avatars;
    let changed = false;
    const next: WatchlistEntry[] = [];
    for (const entry of entries.value) {
      if (!missingIds.has(entry.id) || currentLiving.has(entry.id)) {
        next.push(entry);
        continue;
      }
      const record = deceasedById.get(entry.id);
      if (!record) {
        changed = true; // No longer part of this world.
        continue;
      }
      const realm = [record.realm_at_death, record.stage_at_death].filter(Boolean).join(' ');
      const updated: WatchlistEntry = {
        id: entry.id,
        name: record.name || entry.name,
        realm: realm || entry.realm,
        deceased: true,
      };
      if (updated.name !== entry.name || updated.realm !== entry.realm || !entry.deceased) {
        changed = true;
      }
      next.push(updated);
    }
    if (changed) commit(next);
  }

  // Scope follows the loaded run; a new full snapshot triggers reconciliation.
  watch(
    () => [worldStore.playthroughId, avatarStore.snapshotRevision] as const,
    ([nextScope, revision], previous) => {
      setScope(nextScope);
      if (revision > 0 && revision !== previous?.[1]) {
        void reconcileSnapshot();
      }
    },
    { immediate: true },
  );

  // An unscoped (in-memory) list belongs to the world that just unloaded.
  watch(() => worldStore.isLoaded, (loaded) => {
    if (!loaded && !scopeId.value) {
      reconcileSeq++;
      entries.value = [];
    }
  });

  // Keep stored snapshots fresh as ticks patch avatars (realm-ups, deaths).
  watch(() => avatarStore.avatars, () => {
    if (entries.value.length > 0) syncFromAvatars();
  });

  return {
    scopeId,
    entries,
    watchedIds,
    watchedIdSet,
    count,
    isWatched,
    add,
    remove,
    toggle,
    clear,
    setScope,
    syncFromAvatars,
    reconcileSnapshot,
  };
});
