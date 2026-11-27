'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { inputClass } from '@/lib/catalog/format';
import { readSavedViews, removeView, saveView, type SavedView } from '@/lib/catalog/views';
import type { Dataset, View } from '@/lib/catalog/types';

export default function SavedViews({
  datasets,
  dataset,
  view,
  open,
}: {
  datasets: Dataset[];
  dataset: Dataset;
  view: View;
  open: (entry: SavedView) => void;
}) {
  const [items, setItems] = useState<SavedView[]>([]);
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    function refresh() {
      try {
        setItems(readSavedViews(datasets));
      } catch {
        setError('Saved views are unavailable in this browser.');
      }
    }
    refresh();
    window.addEventListener('storage', refresh);
    return () => window.removeEventListener('storage', refresh);
  }, [datasets]);

  function save(event: FormEvent) {
    event.preventDefault();
    try {
      setItems(saveView(datasets, { name, dataset: dataset.id, view }));
      setName('');
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save this view.');
    }
  }

  function remove(entry: SavedView) {
    try {
      setItems(removeView(datasets, entry));
      setError('');
    } catch {
      setError('Could not remove the saved view.');
    }
  }

  return (
    <details className="panel-muted p-3">
      <summary className="cursor-pointer text-sm font-medium">Saved views ({items.length})</summary>
      <form className="my-3 flex flex-wrap items-end gap-2" onSubmit={save}>
        <label className="text-xs">
          Name this view
          <input
            required
            maxLength={64}
            className={`${inputClass} mt-1 block`}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <button className="btn-secondary" disabled={!name.trim()}>
          Save on this device
        </button>
      </form>
      {error && (
        <p className="text-sm text-rose-300" role="alert">
          {error}
        </p>
      )}
      <ul className="space-y-1">
        {items.map((entry) => (
          <li
            key={JSON.stringify([entry.dataset, entry.name])}
            className="flex items-center justify-between gap-3 border-t border-white/10 py-2 text-sm"
          >
            <button className="text-left underline" onClick={() => open(entry)}>
              {entry.name} · {datasets.find((item) => item.id === entry.dataset)?.label}
            </button>
            <button
              className="text-white/60"
              onClick={() => remove(entry)}
              aria-label={`Remove saved view ${entry.name}`}
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
    </details>
  );
}
