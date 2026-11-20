import { defineStore } from 'pinia';
import { ref, shallowRef } from 'vue';
import type { GameEvent } from '../types/core';
import type { FetchEventsParams, EventDTO } from '../types/api';
import { eventApi } from '../api';
import { processNewEvents, mergeAndSortEvents } from '../utils/eventHelper';
import { mapEventDtosToTimeline } from '../api/mappers/event';
import { logError } from '../utils/appError';

export const useEventStore = defineStore('event', () => {
  const events = shallowRef<GameEvent[]>([]);

  // Pagination state
  const eventsCursor = ref<string | null>(null);
  const eventsHasMore = ref(false);
  const eventsLoading = ref(false);
  const eventsFilter = ref<FetchEventsParams>({});
  const lastMergeDurationMs = ref(0);
  const lastLoadDurationMs = ref(0);

  // Request counter
  let eventsRequestId = 0;

  function matchesMajorScope(event: GameEvent, majorScope: FetchEventsParams['major_scope']) {
    if (!majorScope || majorScope === 'all') return true;
    if (majorScope === 'major') return event.isMajor && !event.isStory;
    return !event.isMajor || event.isStory;
  }

  function addEvents(rawEvents: EventDTO[], currentYear: number, currentMonth: number) {
    if (!rawEvents || rawEvents.length === 0) return;
    const mergeStart = performance.now();

    let newEvents = processNewEvents(rawEvents, currentYear, currentMonth);

    // Filter by the current filter (data stays in SQLite)
    const filter = eventsFilter.value;
    if (filter.avatar_id) {
      newEvents = newEvents.filter(e =>
        e.relatedAvatarIds?.includes(filter.avatar_id!)
      );
    } else if (filter.avatar_ids?.length) {
      const wanted = new Set(filter.avatar_ids);
      newEvents = newEvents.filter(e =>
        e.relatedAvatarIds?.some(id => wanted.has(id))
      );
    } else if (filter.avatar_id_1 && filter.avatar_id_2) {
      newEvents = newEvents.filter(e =>
        e.relatedAvatarIds?.includes(filter.avatar_id_1!) &&
        e.relatedAvatarIds?.includes(filter.avatar_id_2!)
      );
    }
    if (filter.sect_id != null) {
      newEvents = newEvents.filter(e => e.relatedSects?.includes(filter.sect_id!));
    }
    if (filter.major_scope) {
      newEvents = newEvents.filter(e => matchesMajorScope(e, filter.major_scope));
    }

    if (newEvents.length === 0) return;

    // Use the shared merge-and-sort helper for correct ordering (createdAt or timestamp)
    events.value = mergeAndSortEvents(events.value, newEvents);
    lastMergeDurationMs.value = performance.now() - mergeStart;
  }

  async function loadEvents(filter: FetchEventsParams = {}, append = false) {
    if (eventsLoading.value) return;
    
    // Bump the counter per request; only accept the latest response.
    const currentRequestId = ++eventsRequestId;
    eventsLoading.value = true;
    const loadStart = performance.now();

    try {
      const params: FetchEventsParams = { ...filter, limit: 100 };
      if (append && eventsCursor.value) {
        params.cursor = eventsCursor.value;
      }

      const res = await eventApi.fetchEvents(params);

      // Drop the response if it is not the latest request.
      if (currentRequestId !== eventsRequestId) {
        return;
      }

      const sortedNewEvents: GameEvent[] = mapEventDtosToTimeline(res.events);

      if (append) {
        // Older events go on top.
        events.value = [...sortedNewEvents, ...events.value];
      } else {
        // Filter changed: replace with API data.
        events.value = sortedNewEvents;
        eventsFilter.value = filter;
      }

      eventsCursor.value = res.nextCursor;
      eventsHasMore.value = res.hasMore;
      lastLoadDurationMs.value = performance.now() - loadStart;
    } catch (e) {
      // Ignore errors from stale requests.
      if (currentRequestId !== eventsRequestId) {
        return;
      }
      logError('EventStore load events', e);
    } finally {
      // Only the latest request updates loading state.
      if (currentRequestId === eventsRequestId) {
        eventsLoading.value = false;
      }
    }
  }

  async function loadMoreEvents() {
    if (!eventsHasMore.value || eventsLoading.value) return;
    await loadEvents(eventsFilter.value, true);
  }

  async function resetEvents(filter: FetchEventsParams = {}) {
    // Invalidate old requests so a new one can start.
    eventsRequestId++;
    eventsLoading.value = false;
    eventsCursor.value = null;
    eventsHasMore.value = false;
    events.value = [];  // Clear old data so stale events do not show after a filter change.
    eventsFilter.value = filter;  // Update the filter now so addEvents filters correctly too.
    await loadEvents(filter, false);
  }

  function reset() {
    events.value = [];
    eventsCursor.value = null;
    eventsHasMore.value = false;
    eventsFilter.value = {};
    eventsRequestId++; // Cancel pending requests
    eventsLoading.value = false;
  }

  return {
    events,
    eventsCursor,
    eventsHasMore,
    eventsLoading,
    eventsFilter,
    lastMergeDurationMs,
    lastLoadDurationMs,
    addEvents,
    loadEvents,
    loadMoreEvents,
    resetEvents,
    reset
  };
});
