'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { catalogRows, catalogSchema, exportReport, saveDownload } from '@/lib/catalog/api';
import { initialView, type ExportFormat, type Schema, type View } from '@/lib/catalog/types';
import { inputClass } from '@/lib/catalog/format';
import FilterBar from './FilterBar';
import ResultsTable from './ResultsTable';
import BreakdownPanel from './BreakdownPanel';
import DistributionPanel from './DistributionPanel';
import QualityPanel from './QualityPanel';
import SavedViews from './SavedViews';

export default function CatalogWorkspace() {
  const query = useQuery({
    queryKey: ['catalog-schema'],
    queryFn: ({ signal }) => catalogSchema(signal),
    staleTime: 300_000,
  });
  if (query.isPending) return <p role="status">Loading catalog…</p>;
  if (query.isError)
    return (
      <div role="alert" className="panel p-5">
        {query.error.message}{' '}
        <button className="btn-secondary" onClick={() => query.refetch()}>
          Retry
        </button>
      </div>
    );
  return <Workspace schema={query.data} />;
}

function Workspace({ schema }: { schema: Schema }) {
  const [key, setKey] = useState(schema.datasets[0].id);
  const dataset = schema.datasets.find((item) => item.id === key)!;
  const [view, setView] = useState(() => initialView(dataset));
  const [revision, setRevision] = useState(0);
  const [tab, setTab] = useState<'records' | 'groups' | 'quality'>('records');
  const [page, setPage] = useState(1);
  const [format, setFormat] = useState<ExportFormat>('csv');
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState('');

  function change(next: View) {
    setView(next);
    setPage(1);
    setError('');
  }

  function activate(id: string, next: View) {
    setKey(id);
    change(next);
    setRevision((n) => n + 1);
    setTab('records');
  }

  const query = useQuery({
    queryKey: ['catalog-rows', key, view, page],
    queryFn: ({ signal }) => catalogRows(key, view, page, signal),
    enabled: tab === 'records',
  });

  async function download() {
    setDownloading(true);
    setError('');
    try {
      const blob = await exportReport(key, view, format);
      saveDownload(blob, `cinetag-${key}.${format}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed.');
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2" aria-label="Catalog tools">
        {(['records', 'groups', 'quality'] as const).map((key) => (
          <button
            key={key}
            aria-pressed={tab === key}
            className={tab === key ? 'btn-primary' : 'btn-secondary'}
            onClick={() => setTab(key)}
          >
            {{ records: 'Records', groups: 'Breakdown', quality: 'Quality checks' }[key]}
          </button>
        ))}
      </div>
      {tab === 'quality' ? (
        <QualityPanel
          open={(check) => {
            const source = schema.datasets.find((item) => item.id === check.dataset)!;
            activate(source.id, initialView(source, check.preset));
          }}
        />
      ) : (
        <>
          <section className="panel-strong space-y-4 p-4 sm:p-5">
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 font-semibold">
                Dataset
                <select
                  className={inputClass}
                  value={key}
                  onChange={(event) => {
                    const source = schema.datasets.find((item) => item.id === event.target.value)!;
                    activate(source.id, initialView(source));
                  }}
                >
                  {schema.datasets.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
              <p className="text-sm text-white/60">{dataset.description}</p>
            </div>
            <FilterBar key={revision} dataset={dataset} view={view} update={change} />
            <SavedViews
              datasets={schema.datasets}
              dataset={dataset}
              view={view}
              open={(entry) => activate(entry.dataset, entry.view)}
            />
          </section>
          <section className="panel-strong space-y-4 p-4 sm:p-5">
            {tab === 'groups' ? (
              <>
                <DistributionPanel
                  key={dataset.id}
                  dataset={dataset}
                  selection={{ search: view.search, filters: view.filters, preset: view.preset }}
                />
                <BreakdownPanel
                  dataset={dataset}
                  selection={{ search: view.search, filters: view.filters, preset: view.preset }}
                  add={(filter) => {
                    change({ ...view, filters: [...view.filters, filter] });
                    setTab('records');
                  }}
                />
              </>
            ) : (
              <>
                {query.isPending && <p role="status">Loading records…</p>}
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
                    <ResultsTable
                      key={JSON.stringify([key, page, view])}
                      dataset={dataset}
                      result={query.data}
                      view={view}
                      setView={change}
                      setPage={setPage}
                    />
                    <div className="flex flex-wrap items-center gap-2 border-t border-white/10 pt-4 text-sm">
                      <label>
                        Export format{' '}
                        <select
                          className={inputClass}
                          value={format}
                          onChange={(e) => setFormat(e.target.value as ExportFormat)}
                        >
                          <option value="csv">CSV</option>
                          <option value="json">JSON</option>
                          <option value="ndjson">NDJSON</option>
                        </select>
                      </label>
                      <button
                        className="btn-secondary"
                        disabled={downloading || query.data.total > schema.export_limit}
                        onClick={download}
                      >
                        {downloading ? 'Exporting…' : 'Export matching records'}
                      </button>
                      {query.data.total > schema.export_limit && (
                        <span>
                          Narrow this selection to {schema.export_limit.toLocaleString()} records to
                          export.
                        </span>
                      )}
                    </div>
                    {error && (
                      <p role="alert" className="text-sm text-rose-300">
                        {error}
                      </p>
                    )}
                  </>
                )}
              </>
            )}
          </section>
        </>
      )}
    </div>
  );
}
