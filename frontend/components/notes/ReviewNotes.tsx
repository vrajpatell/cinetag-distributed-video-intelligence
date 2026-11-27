'use client';

import { useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { createNote, listNotes, type NoteState } from '@/lib/catalog/notes';
import NoteCard from './NoteCard';
import NoteForm from './NoteForm';

export default function ReviewNotes({
  videoId,
  duration,
}: {
  videoId: number | string;
  duration?: number;
}) {
  const [open, setOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const [state, setState] = useState<NoteState | 'all'>('open');
  const [page, setPage] = useState(1);
  const request = useRef<{ id: string; signature: string } | null>(null);
  const client = useQueryClient();
  const prefix = ['video-notes', String(videoId)];
  const query = useQuery({
    queryKey: [...prefix, state, page],
    queryFn: ({ signal }) => listNotes(videoId, state, page, signal),
    enabled: open,
  });
  const refresh = async () => {
    await client.invalidateQueries({ queryKey: prefix });
  };
  return (
    <details className="panel-strong p-5" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary className="cursor-pointer font-semibold">Review notes</summary>
      {open && (
        <div className="mt-4 space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            {(['open', 'resolved', 'all'] as const).map((value) => {
              const count =
                query.data &&
                (value === 'all'
                  ? query.data.open_count + query.data.resolved_count
                  : value === 'open'
                    ? query.data.open_count
                    : query.data.resolved_count);
              return (
                <button
                  type="button"
                  key={value}
                  aria-pressed={state === value}
                  className="chip-neutral capitalize aria-pressed:bg-white/20"
                  onClick={() => {
                    setState(value);
                    setPage(1);
                  }}
                >
                  {value}
                  {count != null ? ` (${count})` : ''}
                </button>
              );
            })}
            {!adding && (
              <button
                className="btn-secondary ml-auto"
                onClick={() => {
                  request.current = null;
                  setAdding(true);
                }}
              >
                Add note
              </button>
            )}
          </div>
          {adding && (
            <NoteForm
              duration={duration}
              label="Save note"
              cancel={() => setAdding(false)}
              save={async (fields) => {
                const signature = JSON.stringify(fields);
                if (request.current?.signature !== signature)
                  request.current = { id: crypto.randomUUID(), signature };
                await createNote(videoId, fields, request.current.id);
                setAdding(false);
                setState('open');
                setPage(1);
                await refresh();
              }}
            />
          )}
          {query.isPending && <p role="status">Loading notes…</p>}
          {query.isError && (
            <p role="alert">
              {query.error.message}{' '}
              <button className="underline" onClick={() => query.refetch()}>
                Retry
              </button>
            </p>
          )}
          {query.data && (
            <>
              {query.data.items.length === 0 && (
                <p className="text-sm text-white/65">No notes on this page.</p>
              )}
              <ul className="space-y-2">
                {query.data.items.map((note) => (
                  <NoteCard key={note.id} note={note} duration={duration} refresh={refresh} />
                ))}
              </ul>
              {(page > 1 || page * query.data.page_size < query.data.total) && (
                <div className="flex items-center gap-3 text-sm">
                  <button
                    className="btn-secondary"
                    disabled={page <= 1}
                    onClick={() => setPage(page - 1)}
                  >
                    Previous
                  </button>
                  <span>Page {page}</span>
                  <button
                    className="btn-secondary"
                    disabled={page * query.data.page_size >= query.data.total}
                    onClick={() => setPage(page + 1)}
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </details>
  );
}
