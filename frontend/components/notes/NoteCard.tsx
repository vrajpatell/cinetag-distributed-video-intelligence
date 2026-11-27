'use client';

import { useState } from 'react';
import { ApiError } from '@/lib/api';
import { editNote, formatNoteTime, type VideoNote } from '@/lib/catalog/notes';
import NoteForm from './NoteForm';
import NoteHistory from './NoteHistory';

export default function NoteCard({
  note,
  duration,
  refresh,
}: {
  note: VideoNote;
  duration?: number;
  refresh: () => Promise<void>;
}) {
  const [editing, setEditing] = useState<VideoNote | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function toggle() {
    setBusy(true);
    setError('');
    try {
      await editNote(note, { state: note.state === 'open' ? 'resolved' : 'open' });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update the note.');
      if (err instanceof ApiError && err.status === 409) await refresh();
    } finally {
      setBusy(false);
    }
  }
  return (
    <li className="space-y-2 rounded-lg border border-white/10 p-3">
      <div className="flex flex-wrap items-center gap-2 text-xs text-white/65">
        <span className="chip-neutral capitalize">{note.category}</span>
        <span>{note.position_ms === null ? 'Whole video' : formatNoteTime(note.position_ms)}</span>
        <span className="capitalize">{note.state}</span>
      </div>
      {editing ? (
        <NoteForm
          initial={editing}
          duration={duration}
          label="Save changes"
          cancel={() => setEditing(null)}
          save={async (fields) => {
            try {
              await editNote(editing, fields);
            } catch (err) {
              if (err instanceof ApiError && err.status === 409) {
                await refresh();
                throw new Error(
                  'Another reviewer changed this note. Your draft is still here. Cancel to read the latest version before editing again.',
                );
              }
              throw err;
            }
            setEditing(null);
            await refresh();
          }}
        />
      ) : (
        <>
          <p className="whitespace-pre-wrap break-words text-sm">{note.body}</p>
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <button className="underline" disabled={busy} onClick={() => setEditing(note)}>
              Edit note
            </button>
            <button className="underline" disabled={busy} onClick={toggle}>
              {note.state === 'open' ? 'Resolve note' : 'Reopen note'}
            </button>
            <time className="text-white/55" dateTime={note.updated_at}>
              Updated {new Date(note.updated_at).toLocaleString()}
            </time>
          </div>
        </>
      )}
      <NoteHistory note={note} />
      {error && (
        <p role="alert" className="text-sm text-rose-300">
          {error}
        </p>
      )}
    </li>
  );
}
