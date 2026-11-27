'use client';

import { useRef, useState } from 'react';
import { saveDownload } from '@/lib/catalog/api';
import { inputClass } from '@/lib/catalog/format';
import { compareSnapshots, readSnapshot, type Trend } from '@/lib/catalog/snapshots';
import type { Quality, QualityCheck } from '@/lib/catalog/types';

const trendLabels: Record<Trend, string> = {
  increased: 'More findings',
  improved: 'Fewer findings',
  unchanged: 'Unchanged',
  added: 'New check',
  removed: 'Retired check',
};

export default function QualitySnapshots({
  report,
  open,
}: {
  report: Quality;
  open: (check: QualityCheck) => void;
}) {
  const [baseline, setBaseline] = useState<Quality | null>(null);
  const [filename, setFilename] = useState('');
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<Trend | 'changes' | 'all'>('changes');
  const sequence = useRef(0);

  async function load(file?: File) {
    if (!file) return;
    const request = ++sequence.current;
    setError('');
    try {
      const snapshot = await readSnapshot(file);
      if (request !== sequence.current) return;
      setBaseline(snapshot);
      setFilename(file.name);
    } catch (err) {
      if (request !== sequence.current) return;
      setBaseline(null);
      setFilename('');
      setError(err instanceof Error ? err.message : 'Could not read this file.');
    }
  }

  function download() {
    const blob = new Blob([JSON.stringify(report, null, 2) + '\n'], { type: 'application/json' });
    const stamp = new Date(report.checked_at).toISOString().replace(/[:.]/g, '-');
    saveDownload(blob, `cinetag-quality-${stamp}.json`);
  }
  const changes = baseline ? compareSnapshots(baseline, report) : [];
  const rows = changes.filter(
    (item) =>
      filter === 'all' ||
      (filter === 'changes' ? item.trend !== 'unchanged' : item.trend === filter),
  );
  return (
    <details className="panel-muted p-4">
      <summary className="cursor-pointer font-semibold">Quality snapshots</summary>
      <div className="mt-3 space-y-4">
        <div className="flex flex-wrap items-end gap-3">
          <button className="btn-secondary" onClick={download}>
            Download current snapshot
          </button>
          <label className="text-sm">
            Compare with a saved snapshot
            <input
              type="file"
              accept=".json,application/json"
              className="mt-1 block max-w-full text-xs"
              onChange={(event) => {
                const file = event.currentTarget.files?.[0];
                event.currentTarget.value = '';
                void load(file);
              }}
            />
          </label>
        </div>
        {error && (
          <p role="alert" className="text-sm text-rose-300">
            {error}
          </p>
        )}
        {baseline && (
          <>
            <p className="break-words text-sm text-white/65">
              Baseline · {filename} · {new Date(baseline.checked_at).toLocaleString()}
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <label className="text-sm">
                Show changes{' '}
                <select
                  className={inputClass}
                  value={filter}
                  onChange={(event) => setFilter(event.target.value as typeof filter)}
                >
                  <option value="changes">All changes</option>
                  <option value="all">All checks</option>
                  {Object.entries(trendLabels).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                className="underline text-sm"
                onClick={() => {
                  sequence.current++;
                  setBaseline(null);
                  setFilename('');
                }}
              >
                Clear baseline
              </button>
            </div>
            {rows.length === 0 ? (
              <p className="text-sm">No checks match this comparison filter.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr>
                      {['Check', 'Baseline', 'Current', 'Difference', 'Change'].map((label) => (
                        <th className="p-2" key={label}>
                          {label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((item) => (
                      <tr key={item.key} className="border-t border-white/10">
                        <td className="p-2">
                          <span className="block text-xs text-white/55">{item.dataset}</span>
                          {item.current ? (
                            <button
                              className="text-left underline"
                              onClick={() => open(item.current!)}
                            >
                              {item.label}
                            </button>
                          ) : (
                            item.label
                          )}
                        </td>
                        <td className="p-2">{item.before ?? '—'}</td>
                        <td className="p-2">{item.after ?? '—'}</td>
                        <td className="p-2 font-mono">
                          {item.delta === null
                            ? '—'
                            : item.delta > 0
                              ? `+${item.delta}`
                              : item.delta}
                        </td>
                        <td className="p-2">{trendLabels[item.trend]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </details>
  );
}
