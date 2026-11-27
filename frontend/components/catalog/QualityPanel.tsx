'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { catalogQuality } from '@/lib/catalog/api';
import QualitySnapshots from './QualitySnapshots';
import { inputClass } from '@/lib/catalog/format';
import type { QualityCheck } from '@/lib/catalog/types';

export default function QualityPanel({ open }: { open: (check: QualityCheck) => void }) {
  const [onlyFindings, setOnlyFindings] = useState(true);
  const [dataset, setDataset] = useState('');
  const query = useQuery({
    queryKey: ['catalog-quality'],
    queryFn: ({ signal }) => catalogQuality(signal),
    staleTime: 60_000,
  });
  if (query.isPending) return <p role="status">Checking catalog metadata…</p>;
  if (query.isError)
    return (
      <p role="alert">
        {query.error.message}{' '}
        <button className="underline" onClick={() => query.refetch()}>
          Try again
        </button>
      </p>
    );
  const checks = query.data.checks;
  const labels = new Map(checks.map((item) => [item.dataset, item.dataset_label]));
  const visible = checks.filter(
    (check) => (!onlyFindings || check.count > 0) && (!dataset || dataset === check.dataset),
  );
  return (
    <section className="space-y-4">
      <QualitySnapshots report={query.data} open={open} />
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm">
          Dataset
          <select
            value={dataset}
            className={inputClass}
            onChange={(event) => setDataset(event.target.value)}
          >
            <option value="">All datasets</option>
            {Array.from(labels).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={onlyFindings}
            onChange={(event) => setOnlyFindings(event.target.checked)}
          />{' '}
          With findings only
        </label>
        <button
          className="btn-secondary"
          disabled={query.isFetching}
          onClick={() => query.refetch()}
        >
          Refresh checks
        </button>
      </div>
      <p className="text-xs text-white/60">
        Checked {new Date(query.data.checked_at).toLocaleString()}
      </p>
      {!visible.length && <p>No checks match these filters.</p>}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {visible.map((check) => (
          <button
            key={`${check.dataset}/${check.preset}`}
            className="panel-muted flex flex-col items-start gap-2 p-4 text-left hover:bg-white/10"
            onClick={() => open(check)}
          >
            <span className="text-xs text-white/65">{check.dataset_label}</span>
            <span className="font-semibold">{check.label}</span>
            <span className="text-sm text-white/70">{check.description}</span>
            <span className="mt-auto pt-2 text-sm underline">
              {check.count.toLocaleString()} matching records
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
