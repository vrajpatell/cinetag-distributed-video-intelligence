'use client';

import { useState, type FormEvent } from 'react';
import { inputClass } from '@/lib/catalog/format';
import {
  formatNoteTime,
  noteCategories,
  parseNoteTime,
  type Category,
  type NoteFields,
} from '@/lib/catalog/notes';

export default function NoteForm({
  initial,
  duration,
  label,
  save,
  cancel,
}: {
  initial?: NoteFields;
  duration?: number;
  label: string;
  save: (fields: NoteFields) => Promise<void>;
  cancel: () => void;
}) {
  const [body, setBody] = useState(initial?.body || '');
  const [category, setCategory] = useState<Category>(initial?.category || 'editorial');
  const [time, setTime] = useState(formatNoteTime(initial?.position_ms ?? null));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      const position = parseNoteTime(time);
      if (position != null && duration && duration > 0 && position > Math.round(duration * 1000))
        throw new Error('Note position exceeds the video duration.');
      await save({ body: body.trim(), category, position_ms: position });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save note.');
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit} className="panel-muted space-y-3 p-3">
      <label className="block text-sm">
        Note
        <textarea
          className={`${inputClass} mt-1 block w-full`}
          required
          rows={3}
          maxLength={4000}
          value={body}
          onChange={(event) => setBody(event.target.value)}
        />
      </label>
      <div className="flex flex-wrap gap-3">
        <label className="text-sm">
          Category
          <select
            className={`${inputClass} mt-1 block capitalize`}
            value={category}
            onChange={(event) => setCategory(event.target.value as Category)}
          >
            {noteCategories.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Time in video (optional)
          <input
            className={`${inputClass} mt-1 block`}
            placeholder="0:00.000"
            value={time}
            maxLength={24}
            onChange={(event) => setTime(event.target.value)}
          />
        </label>
      </div>
      {error && (
        <p role="alert" className="text-sm text-rose-300">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <button type="submit" disabled={busy || !body.trim()} className="btn-primary">
          {busy ? 'Saving…' : label}
        </button>
        <button type="button" disabled={busy} className="btn-secondary" onClick={cancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
