import { httpClient } from '../http';
import type {
  EventExportParams,
  EventsResponseDTO,
  FetchEventsParams
} from '../../types/api';
import { normalizeEventsResponse } from '../mappers/event';

const EVENT_EXPORT_PATH = '/api/v1/query/events/export';
const EVENT_EXPORT_TIMEOUT_MS = 120000;

export function buildEventExportPath(params: EventExportParams): string {
  const query = new URLSearchParams();
  query.set('format', params.format);
  if (params.avatar_id) query.set('avatar_id', params.avatar_id);
  if (params.major_only) query.set('major_only', 'true');
  if (params.from_year != null) query.set('from_year', String(params.from_year));
  if (params.to_year != null) query.set('to_year', String(params.to_year));
  return `${EVENT_EXPORT_PATH}?${query}`;
}

export const eventApi = {
  downloadEventExport(params: EventExportParams) {
    return httpClient.download(buildEventExportPath(params), { timeoutMs: EVENT_EXPORT_TIMEOUT_MS });
  },

  async fetchEvents(params: FetchEventsParams = {}) {
    const query = new URLSearchParams();
    if (params.avatar_id) query.set('avatar_id', params.avatar_id);
    if (params.avatar_id_1) query.set('avatar_id_1', params.avatar_id_1);
    if (params.avatar_id_2) query.set('avatar_id_2', params.avatar_id_2);
    if (params.avatar_ids?.length) query.set('avatar_ids', params.avatar_ids.join(','));
    if (params.sect_id != null) query.set('sect_id', String(params.sect_id));
    if (params.major_scope && params.major_scope !== 'all') query.set('major_scope', params.major_scope);
    if (params.cursor) query.set('cursor', params.cursor);
    if (params.limit) query.set('limit', String(params.limit));
    const qs = query.toString();
    const data = await httpClient.get<EventsResponseDTO>(`/api/v1/query/events${qs ? '?' + qs : ''}`);
    return normalizeEventsResponse(data);
  },

  cleanupEvents(keepMajor = true, beforeMonthStamp?: number) {
    const query = new URLSearchParams();
    query.set('keep_major', String(keepMajor));
    if (beforeMonthStamp !== undefined) query.set('before_month_stamp', String(beforeMonthStamp));
    return httpClient.delete<{ deleted: number }>(`/api/v1/command/events/cleanup?${query}`);
  }
};
