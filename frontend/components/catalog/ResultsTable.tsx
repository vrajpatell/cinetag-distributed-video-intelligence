'use client';

import Link from 'next/link';
import { useState } from 'react';
import { displayCell, inputClass } from '@/lib/catalog/format';
import type { Dataset, RecordRow, Results, View } from '@/lib/catalog/types';

interface Props {
  dataset: Dataset;
  result: Results;
  view: View;
  setView: (view: View) => void;
  setPage: (page: number) => void;
}

function RowDetails({ dataset, row }: { dataset: Dataset; row: RecordRow }) {
  return (
    <dl className="grid gap-3 p-3 md:grid-cols-2">
      {dataset.fields
        .filter((field) => field.id in row.cells)
        .map((field) => (
          <div key={field.id}>
            <dt className="text-xs font-semibold text-white/60">{field.label}</dt>
            <dd className="mt-1 whitespace-pre-wrap break-words text-sm">
              {displayCell(row.cells[field.id], field.kind)}
            </dd>
          </div>
        ))}
      {row.video_id != null && (
        <div>
          <Link className="underline" href={`/videos/${row.video_id}`}>
            Open video
          </Link>
        </div>
      )}
    </dl>
  );
}

export default function ResultsTable({ dataset, result, view, setView, setPage }: Props) {
  const [expanded, setExpanded] = useState<number | null>(null);
  const columns = result.columns.map((key) => dataset.fields.find((field) => field.id === key)!);
  const pages = Math.max(1, Math.ceil(result.total / result.page_size));
  return (
    <section aria-label="Catalog results" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm text-white/70">
          {result.total.toLocaleString()} matching records
        </span>
        <details className="relative">
          <summary className="cursor-pointer text-sm underline">Columns</summary>
          <fieldset className="absolute right-0 z-10 mt-2 max-h-72 w-56 space-y-2 overflow-y-auto rounded-lg border border-white/15 bg-zinc-950 p-3 shadow-xl">
            <legend className="sr-only">Visible columns</legend>
            {dataset.fields.map((col) => {
              const checked = view.columns.includes(col.id);
              return (
                <label key={col.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={checked && view.columns.length === 1}
                    onChange={() =>
                      setView({
                        ...view,
                        columns: checked
                          ? view.columns.filter((key) => key !== col.id)
                          : [...view.columns, col.id],
                      })
                    }
                  />
                  {col.label}
                </label>
              );
            })}
          </fieldset>
        </details>
      </div>
      {result.rows.length ? (
        <div className="overflow-x-auto rounded-lg border border-white/10">
          <table className="w-full border-collapse text-left text-sm">
            <thead className="bg-white/5 text-xs">
              <tr>
                <th className="p-3">Record</th>
                {columns.map((col) => (
                  <th
                    key={col.id}
                    scope="col"
                    className="whitespace-nowrap p-3"
                    aria-sort={
                      view.sort.field !== col.id
                        ? 'none'
                        : view.sort.direction === 'asc'
                          ? 'ascending'
                          : 'descending'
                    }
                  >
                    <button
                      type="button"
                      onClick={() =>
                        setView({
                          ...view,
                          sort: {
                            field: col.id,
                            direction:
                              view.sort.field === col.id && view.sort.direction === 'asc'
                                ? 'desc'
                                : 'asc',
                          },
                        })
                      }
                    >
                      {col.label}{' '}
                      {view.sort.field === col.id
                        ? view.sort.direction === 'asc'
                          ? '↑'
                          : '↓'
                        : ''}
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            {result.rows.map((row) => (
              <tbody key={row.id} className="border-t border-white/10">
                <tr>
                  <td className="p-3">
                    <button
                      type="button"
                      className="whitespace-nowrap font-mono underline"
                      aria-expanded={expanded === row.id}
                      aria-label={`Details for record ${row.id}`}
                      onClick={() => setExpanded(expanded === row.id ? null : row.id)}
                    >
                      #{row.id}
                    </button>
                  </td>
                  {columns.map((col) => (
                    <td
                      key={col.id}
                      className="max-w-64 truncate p-3"
                      title={String(row.cells[col.id] ?? '')}
                    >
                      {displayCell(row.cells[col.id], col.kind)}
                    </td>
                  ))}
                </tr>
                {expanded === row.id && (
                  <tr>
                    <td colSpan={columns.length + 1} className="bg-white/5">
                      <RowDetails row={row} dataset={dataset} />
                    </td>
                  </tr>
                )}
              </tbody>
            ))}
          </table>
        </div>
      ) : (
        <p className="rounded-lg border border-white/10 p-5 text-sm">
          No records match this selection.
        </p>
      )}
      <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
        <label className="flex items-center gap-2">
          Rows per page
          <select
            className={inputClass}
            value={view.page_size}
            onChange={(event) => setView({ ...view, page_size: Number(event.target.value) })}
          >
            {[10, 25, 50, 100].map((n) => (
              <option key={n}>{n}</option>
            ))}
          </select>
        </label>
        <div className="flex items-center gap-3">
          <button
            className="btn-secondary"
            disabled={result.page <= 1}
            onClick={() => setPage(Math.max(1, Math.min(pages, result.page - 1)))}
          >
            Previous
          </button>
          <span>
            Page {result.page} of {pages}
          </span>
          <button
            className="btn-secondary"
            disabled={result.page >= pages}
            onClick={() => setPage(result.page + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}
