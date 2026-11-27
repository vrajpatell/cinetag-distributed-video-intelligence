'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { catalogRows } from '@/lib/catalog/api';
import { inputClass } from '@/lib/catalog/format';
import type { AssetRef } from '@/lib/catalog/compare';

export default function AssetPicker({
  label,
  selected,
  excluded,
  onSelect,
}: {
  label: string;
  selected: AssetRef | null;
  excluded?: number;
  onSelect: (asset: AssetRef) => void;
}) {
  const [search, setSearch] = useState('');
  const [term, setTerm] = useState('');
  const [open, setOpen] = useState(false);
  const query = useQuery({
    queryKey: ['compare-picker', term],
    queryFn: ({ signal }) =>
      catalogRows(
        'videos',
        {
          search: term,
          filters: [],
          preset: null,
          sort: { field: 'id', direction: 'desc' },
          columns: ['title', 'original_filename'],
          page_size: 10,
        },
        1,
        signal,
      ),
    enabled: open,
  });
  return (
    <div className="panel-muted space-y-3 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs text-white/60">{label}</p>
          <p className="font-semibold">{selected?.title || 'Choose a video'}</p>
        </div>
        <button
          type="button"
          className="btn-secondary"
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          {open ? 'Close list' : `Select ${label.toLowerCase()}`}
        </button>
      </div>
      {open && (
        <>
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              setTerm(search.trim());
            }}
          >
            <input
              aria-label={`Search for ${label.toLowerCase()}`}
              type="search"
              maxLength={256}
              className={`${inputClass} min-w-0 flex-1`}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button className="btn-secondary">Search</button>
          </form>
          {query.isPending && <p role="status">Looking up videos…</p>}
          {query.isError && <p role="alert">{query.error.message}</p>}
          <ul className="max-h-56 overflow-y-auto text-sm">
            {query.data?.rows.map((row) => {
              const title = String(
                row.cells.title || row.cells.original_filename || `Video #${row.id}`,
              );
              return (
                <li key={row.id}>
                  <button
                    type="button"
                    disabled={row.id === excluded}
                    className="w-full rounded px-2 py-2 text-left hover:bg-white/10 disabled:opacity-40"
                    onClick={() => {
                      onSelect({ id: row.id, title });
                      setOpen(false);
                    }}
                  >
                    {title} · #{row.id}
                  </button>
                </li>
              );
            })}
          </ul>
          {query.data && query.data.rows.length === 0 && (
            <p className="text-sm">No videos found.</p>
          )}
          {query.data && query.data.total > query.data.rows.length && (
            <p className="text-xs text-white/60">
              Showing the first 10 matches. Refine your search to find another video.
            </p>
          )}
        </>
      )}
    </div>
  );
}
