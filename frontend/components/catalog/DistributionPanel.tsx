'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { catalogDistribution } from '@/lib/catalog/api';
import { displayCell, inputClass } from '@/lib/catalog/format';
import type { Dataset, Selection, Distribution } from '@/lib/catalog/types';

const summaries = [
  ['minimum', 'Minimum'],
  ['median', 'Median (p50)'],
  ['mean', 'Mean'],
  ['p90', '90th percentile'],
  ['p95', '95th percentile'],
  ['maximum', 'Maximum'],
] as const satisfies ReadonlyArray<readonly [keyof Distribution, string]>;

export default function DistributionPanel({
  dataset,
  selection,
}: {
  dataset: Dataset;
  selection: Selection;
}) {
  const measures = dataset.fields.filter(field => field.measurable);
  const [active, setActive] = useState(false);
  const [key, setKey] = useState(measures[0]?.id || '');
  const field = measures.find((candidate) => candidate.id === key);
  const query = useQuery({
    queryKey: ['catalog-distribution', dataset.id, selection, key],
    queryFn: ({ signal }) => catalogDistribution(dataset.id, selection, key, signal),
    enabled: active && !!field,
  });
  if (!field) return null;
  return (
    <details className="panel-muted p-4" onToggle={(e) => setActive(e.currentTarget.open)}>
      <summary className="cursor-pointer text-sm font-semibold">Measurement statistics</summary>
      {active && (
        <div className="mt-3 space-y-3">
          <label className="text-sm">
            Measurement{' '}
            <select className={inputClass} value={key} onChange={(e) => setKey(e.target.value)}>
              {measures.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          {query.isPending && <p role="status">Calculating percentiles…</p>}
          {query.isError && <p role="alert">{query.error.message}</p>}
          {query.data && (
            <>
              <p className="text-sm text-white/60">
                {query.data.measured.toLocaleString()} measured ·{' '}
                {query.data.missing.toLocaleString()} missing
              </p>
              {query.data.measured > 0 && (
                <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {summaries.map(([id, label]) => (
                    <div key={id} className="rounded-md bg-white/5 p-3">
                      <dt className="text-xs text-white/60">{label}</dt>
                      <dd className="mt-1 font-mono" title={String(query.data[id])}>
                        {displayCell(query.data[id], field.kind)}
                      </dd>
                    </div>
                  ))}
                </dl>
              )}
            </>
          )}
        </div>
      )}
    </details>
  );
}
