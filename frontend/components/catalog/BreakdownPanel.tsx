'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { catalogBreakdown } from '@/lib/catalog/api';
import { displayCell, inputClass } from '@/lib/catalog/format';
import type { Dataset, Filter, Selection } from '@/lib/catalog/types';

export default function BreakdownPanel({
  dataset,
  selection,
  add,
}: {
  dataset: Dataset;
  selection: Selection;
  add: (rule: Filter) => void;
}) {
  const fields = dataset.fields.filter((col) => col.groupable);
  const [key, setKey] = useState(fields[0]?.id || '');
  const field = fields.find((col) => col.id === key);
  const query = useQuery({
    queryKey: ['catalog-breakdown', dataset.id, selection, key],
    queryFn: ({ signal }) => catalogBreakdown(dataset.id, selection, key, signal),
    enabled: !!field,
  });
  if (!field) return <p className="text-sm text-white/65">This dataset has no grouped fields.</p>;
  return (
    <div className="space-y-4">
      <label className="flex items-center gap-3 text-sm">
        Group by
        <select className={inputClass} value={key} onChange={(event) => setKey(event.target.value)}>
          {fields.map((col) => (
            <option key={col.id} value={col.id}>
              {col.label}
            </option>
          ))}
        </select>
      </label>
      {query.isPending && <p role="status">Counting matching records…</p>}
      {query.isError && <p role="alert">{query.error.message}</p>}
      {query.data && (
        <div>
          <p className="mb-3 text-sm text-white/65">
            {query.data.total.toLocaleString()} matching records
          </p>
          <ul className="space-y-2">
            {query.data.groups.map((group) => {
              const share = group.count / query.data.total;
              const label =
                group.value === null ? 'No value' : displayCell(group.value, field.kind);
              // SQL groups NULL and empty strings separately; the presence filter combines them.
              const drillable =
                group.value !== null && group.value !== '' && selection.filters.length < 12;
              return (
                <li
                  key={JSON.stringify(group.value)}
                  className="grid grid-cols-[minmax(7rem,1fr)_2fr_auto] items-center gap-3 text-sm"
                >
                  {drillable ? (
                    <button
                      type="button"
                      className="break-words text-left underline"
                      onClick={() =>
                        add({ field: key, operator: 'eq', value: String(group.value) })
                      }
                    >
                      {label}
                    </button>
                  ) : (
                    <span>{label}</span>
                  )}
                  <div className="h-2 rounded bg-white/10" aria-hidden>
                    <div
                      className="h-full rounded bg-rose-400"
                      style={{ width: `${share * 100}%` }}
                    />
                  </div>
                  <span>
                    {group.count.toLocaleString()} ({(share * 100).toFixed(1)}%)
                  </span>
                </li>
              );
            })}
          </ul>
          {query.data.remaining > 0 && (
            <p className="mt-2 text-sm text-white/60">
              Other groups · {query.data.remaining.toLocaleString()} records
            </p>
          )}
        </div>
      )}
    </div>
  );
}
