import type { EventDTO } from '@/types/api';
import type { GameEvent } from '../types/core';

export const MAX_EVENTS = 300;

/**
 * Convert incoming events into domain objects and assign sequence numbers
 */
export function processNewEvents(rawEvents: EventDTO[], currentYear: number, currentMonth: number): GameEvent[] {
  if (!rawEvents || rawEvents.length === 0) return [];

  return rawEvents.map((e, index) => ({
    id: e.id,
    text: e.text,
    content: e.content,
    year: e.year ?? currentYear,
    month: e.month ?? currentMonth,
    timestamp: (e.year ?? currentYear) * 12 + (e.month ?? currentMonth),
    relatedAvatarIds: e.related_avatar_ids || [],
    relatedSects: e.related_sects,
    subjects: (e.subjects || []).map((subject) => {
      if (subject.type === 'sect') {
        return {
          type: 'sect' as const,
          id: subject.id,
          name: subject.name,
          color: subject.color,
          isActive: subject.is_active,
        };
      }
      return {
        type: 'avatar' as const,
        id: subject.id,
        name: subject.name,
        color: subject.color || avatarIdToColor(subject.id),
        isDead: subject.is_dead,
      };
    }),
    isMajor: e.is_major,
    isStory: e.is_story,
    renderKey: e.render_key,
    renderParams: e.render_params,
    createdAt: e.created_at,
    _seq: index 
  }));
}

/**
 * Merge and sort event lists
 * 1. createdAt (precise timestamp) ascending first
 * 2. then month stamp ascending
 * 3. then sequence number ascending
 * 4. keep the newest MAX_EVENTS
 */
export function mergeAndSortEvents(existingEvents: GameEvent[], newEvents: GameEvent[]): GameEvent[] {
  // Merge
  const combined = [...existingEvents]; // Copy existing
  // Add new ones only if not exists (by id)
  const existingIds = new Set(existingEvents.map(e => e.id));
  for (const ev of newEvents) {
      if (!existingIds.has(ev.id)) {
          combined.push(ev);
      }
  }
  
  combined.sort((a, b) => {
    // 0. Compare createdAt first when both have it
    // Note: SQLite may return no createdAt (or 0) for historical data
    if (a.createdAt && b.createdAt && a.createdAt > 0 && b.createdAt > 0) {
        // float comparison
        return a.createdAt - b.createdAt;
    }

    // 1. Timestamp ascending (oldest month on top)
    const ta = a.timestamp;
    const tb = b.timestamp;
    if (tb !== ta) {
      return ta - tb;
    }
    
    // 2. Same time: original logical order ascending (earlier first)
    // If only one has createdAt (unlikely unless mixed with old data)
    // we assume both tick and API data carry createdAt.
    
    // Without createdAt, fall back to _seq
    const seqA = a._seq ?? -1;
    const seqB = b._seq ?? -1;
    
    if (seqA === -1 && seqB === -1) return 0;
    
    return seqA - seqB;
  });
  
  // Keep the newest N
  if (combined.length > MAX_EVENTS) {
    return combined.slice(-MAX_EVENTS);
  }
  
  return combined;
}

/**
 * Derive a stable HSL color from a hash of the avatar ID.
 */
export function avatarIdToColor(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = ((hash << 5) - hash) + id.charCodeAt(i);
    hash |= 0;
  }
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 70%, 65%)`;
}

export interface AvatarColorInfo {
  id: string;
  color: string;
}

export interface SectColorInfo {
  id: number;
  color: string;
}

export interface EventContentToken {
  type: 'text' | 'avatar' | 'sect';
  text: string;
  avatarId?: string;
  sectId?: number;
  color?: string;
}

/**
 * Build a name -> { id, color } map from the avatar list.
 */
export function buildAvatarColorMap(
  avatars: Array<{ id: string; name?: string }>
): Map<string, AvatarColorInfo> {
  const map = new Map<string, AvatarColorInfo>();
  for (const av of avatars) {
    if (av.name) {
      map.set(av.name, { id: av.id, color: avatarIdToColor(av.id) });
    }
  }
  return map;
}

/**
 * Build a name -> { id, color } map from the sect list.
 * Colors come from sect.csv via the backend; white when missing.
 */
export function buildSectColorMap(
  sects: Array<{ sect_id?: number; sect_name?: string; sect_color?: string }>
): Map<string, SectColorInfo> {
  const map = new Map<string, SectColorInfo>();
  for (const sect of sects) {
    const id = sect.sect_id;
    const name = sect.sect_name;
    if (id == null || !name) continue;
    map.set(name, { id, color: sect.sect_color || '#FFFFFF' });
  }
  return map;
}

const HTML_ESCAPE_MAP: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
};

export function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, c => HTML_ESCAPE_MAP[c] || c);
}

/**
 * Split event text into safe render tokens so components avoid v-html.
 */
export function tokenizeEventContent(
  text: string,
  colorMap: Map<string, AvatarColorInfo>,
  sectColorMap: Map<string, SectColorInfo> = new Map()
): EventContentToken[] {
  if (!text) return [];
  const entityByName = new Map<string, { type: 'avatar' | 'sect'; id: string | number; color: string }>();
  for (const [name, info] of colorMap.entries()) {
    entityByName.set(name, { type: 'avatar', id: info.id, color: info.color });
  }
  // On name clashes avatars win, preserving existing behavior.
  for (const [name, info] of sectColorMap.entries()) {
    if (!entityByName.has(name)) {
      entityByName.set(name, { type: 'sect', id: info.id, color: info.color });
    }
  }

  if (entityByName.size === 0) {
    return [{ type: 'text', text }];
  }

  const names = [...entityByName.keys()].sort((a, b) => b.length - a.length);
  const escapeRegex = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const pattern = new RegExp(names.map(escapeRegex).join('|'), 'g');

  const tokens: EventContentToken[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    const start = match.index;
    const matchedText = match[0];

    if (start > lastIndex) {
      tokens.push({
        type: 'text',
        text: text.slice(lastIndex, start),
      });
    }

    const info = entityByName.get(matchedText);
    if (info?.type === 'avatar') {
      tokens.push({
        type: 'avatar',
        text: matchedText,
        avatarId: String(info.id),
        color: info.color,
      });
    } else if (info?.type === 'sect') {
      tokens.push({
        type: 'sect',
        text: matchedText,
        sectId: Number(info.id),
        color: info.color,
      });
    } else {
      // Should be unreachable; fall back to plain text to avoid render errors.
      tokens.push({
        type: 'text',
        text: matchedText,
      });
    }

    lastIndex = start + matchedText.length;
  }

  if (lastIndex < text.length) {
    tokens.push({
      type: 'text',
      text: text.slice(lastIndex),
    });
  }

  return tokens;
}

/**
 * Highlight avatar names in text and return an HTML string.
 * Each span has a data-avatar-id attribute for click-through.
 *
 * Implementation notes:
 * - Uses a single regex replace (not repeated replaceAll) to handle overlapping names.
 * - E.g. with "Zhang San" and "Zhang Sanfeng", repeated replaceAll would wrongly match "Zhang San" inside "Zhang Sanfeng".
 * - A single /(Zhang Sanfeng|Zhang San)/g with longer names first consumes "Zhang Sanfeng" as a whole,
 *   so "Zhang San" is never matched inside it.
 * - The /g flag replaces every occurrence (one pass, callback called per match).
 */
export function highlightAvatarNames(
  text: string,
  colorMap: Map<string, AvatarColorInfo>
): string {
  if (!text) return text;

  return tokenizeEventContent(text, colorMap)
    .map((token) => {
      if (token.type === 'avatar') {
        return `<span class="clickable-avatar" data-avatar-id="${token.avatarId}" style="color:${token.color};cursor:pointer">${escapeHtml(token.text)}</span>`;
      }
      return escapeHtml(token.text);
    })
    .join('');
}

