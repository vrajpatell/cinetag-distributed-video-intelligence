import { apiFetch } from '@/lib/api';

export const noteCategories = ['editorial', 'audio', 'visual', 'transcript', 'tags'] as const;
export type Category = (typeof noteCategories)[number];
export type NoteState = 'open' | 'resolved';

export interface NoteFields {
  category: Category;
  position_ms: number | null;
  body: string;
}
export interface VideoNote extends NoteFields {
  id: number;
  video_id: number;
  state: NoteState;
  revision: number;
  created_at: string;
  updated_at: string;
}
export interface NotePage {
  items: VideoNote[];
  total: number;
  open_count: number;
  resolved_count: number;
  page: number;
  page_size: number;
}

function path(id: number | string) {
  return `/api/videos/${encodeURIComponent(id)}/notes`;
}

export function listNotes(
  id: number | string,
  state: NoteState | 'all',
  page: number,
  signal?: AbortSignal,
) {
  const query = new URLSearchParams({ page: String(page), page_size: '10' });
  if (state !== 'all') query.set('state', state);
  return apiFetch<NotePage>(`${path(id)}?${query}`, { signal });
}

export function createNote(id: number | string, fields: NoteFields, requestId: string) {
  return apiFetch<VideoNote>(path(id), {
    method: 'POST',
    body: JSON.stringify({ ...fields, request_id: requestId }),
  });
}

export function editNote(note: VideoNote, changes: Partial<NoteFields & { state: NoteState }>) {
  return apiFetch<VideoNote>(`${path(note.video_id)}/${note.id}`, {
    method: 'PATCH',
    body: JSON.stringify({ ...changes, revision: note.revision }),
  });
}

export function formatNoteTime(value: number | null) {
  if (value === null) return '';
  const millis = String(value % 1000)
    .padStart(3, '0')
    .replace(/0+$/, '');
  const total = Math.floor(value / 1000);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = String(total % 60).padStart(2, '0');
  return (
    (hours ? `${hours}:${String(minutes).padStart(2, '0')}` : String(minutes)) +
    `:${seconds}` +
    (millis ? `.${millis}` : '')
  );
}

export function parseNoteTime(input: string) {
  const value = input.trim();
  if (value === '') return null;
  if (!/^\d+(?::\d{1,2}){0,2}(?:\.\d{1,3})?$/.test(value))
    throw new Error('Enter seconds or a time such as 1:24.500.');
  const parts = value.split(':').map(Number);
  if (parts.slice(1).some((part) => part >= 60))
    throw new Error('Minutes and seconds after a colon must be less than 60.');
  const result = Math.round(parts.reduce((total, part) => total * 60 + part, 0) * 1000);
  if (!Number.isSafeInteger(result) || result > 2147483647)
    throw new Error('Time exceeds the supported range.');
  return result;
}

interface Revision {
  revision: number;
  state: NoteState;
  category: Category;
  position_ms: number | null;
}

export interface RevisionEvent {
  id: number;
  timestamp: string;
  previous: Revision | null;
  current: Revision;
}

interface HistoryPage {
  items: RevisionEvent[];
  next_before: number | null;
}

export function noteHistory(note: VideoNote, before: number | null, signal?: AbortSignal) {
  const cursor = before === null ? '' : `?before=${before}`;
  return apiFetch<HistoryPage>(`${path(note.video_id)}/${note.id}/history${cursor}`, { signal });
}
