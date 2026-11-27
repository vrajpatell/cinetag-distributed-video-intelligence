'use client';

import { useState } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import {
  formatNoteTime,
  noteHistory,
  type RevisionEvent,
  type VideoNote,
} from '@/lib/catalog/notes';

function changes(event: RevisionEvent) {
  const { current, previous } = event;
  if (!previous) return ['Note created'];
  const details = [];
  if (current.state !== previous.state) {
    details.push(current.state === 'resolved' ? 'Marked resolved' : 'Reopened');
  }
  if (current.category !== previous.category) {
    details.push(`Category changed from ${previous.category} to ${current.category}`);
  }
  if (current.position_ms !== previous.position_ms) {
    const from = formatNoteTime(previous.position_ms) || 'whole video';
    const to = formatNoteTime(current.position_ms) || 'whole video';
    details.push(`Position changed from ${from} to ${to}`);
  }
  return details.length ? details : ['Note updated'];
}

export default function NoteHistory({ note }: { note: VideoNote }) {
  const [open, setOpen] = useState(false);
  const query = useInfiniteQuery({
    queryKey: ['note-history', note.video_id, note.id, note.revision],
    queryFn: ({ pageParam, signal }) => noteHistory(note, pageParam, signal),
    initialPageParam: null as number | null,
    getNextPageParam: (page) => page.next_before ?? undefined,
    enabled: open,
  });
  return (
    <details className="text-xs" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary className="cursor-pointer text-white/65">Revision history</summary>
      {open && (
        <div className="mt-2 space-y-2">
          {query.isPending && <p role="status">Loading revisions…</p>}
          {query.isError && (
            <p role="alert">
              {query.error.message}{' '}
              <button className="underline" onClick={() => query.refetch()}>
                Retry
              </button>
            </p>
          )}
          {query.data && (
            <ol className="space-y-2 border-l border-white/15 pl-3">
              {query.data.pages
                .flatMap((page) => page.items)
                .map((event) => (
                  <li key={event.id}>
                    <div className="text-white/65">
                      Revision {event.current.revision} ·{' '}
                      <time dateTime={event.timestamp}>
                        {new Date(event.timestamp).toLocaleString()}
                      </time>
                    </div>
                    {changes(event).map((line) => (
                      <div key={line}>{line}</div>
                    ))}
                  </li>
                ))}
            </ol>
          )}
          {query.hasNextPage && (
            <button
              type="button"
              className="underline"
              disabled={query.isFetchingNextPage}
              onClick={() => query.fetchNextPage()}
            >
              Older revisions
            </button>
          )}
        </div>
      )}
    </details>
  );
}
