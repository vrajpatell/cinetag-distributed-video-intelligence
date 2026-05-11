'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import JobStatusBadge from '@/components/JobStatusBadge';
import EmptyState from '@/components/EmptyState';
import PipelineFlow from '@/components/PipelineFlow';
import { ApiError, getJobs, retryJob } from '@/lib/api';
import { DEMO_JOBS } from '@/lib/demo-data';
import { formatRelativeTime } from '@/lib/format';
import type { JobSummary } from '@/lib/types';

const STATUS_FILTERS = ['all', 'queued', 'running', 'completed', 'failed', 'partially_completed'] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [usedDemo, setUsedDemo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<StatusFilter>('all');
  const [retrying, setRetrying] = useState<string | number | null>(null);

  const load = useCallback(async () => {
    try {
      const real = await getJobs({ page_size: 100 });
      if (real.items.length > 0) {
        setJobs(real.items);
        setUsedDemo(false);
      } else {
        setJobs(DEMO_JOBS);
        setUsedDemo(true);
      }
      setError(null);
    } catch (err) {
      setJobs(DEMO_JOBS);
      setUsedDemo(true);
      setError(
        err instanceof ApiError
          ? `Could not reach jobs API (${err.status ?? 'network error'}). Showing demo data.`
          : 'Could not reach jobs API. Showing demo data.'
      );
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 15_000);
    return () => clearInterval(id);
  }, [load]);

  const summary = useMemo(() => {
    const list = jobs || [];
    return {
      total: list.length,
      queued: list.filter((j) => j.status === 'queued').length,
      running: list.filter((j) => j.status === 'running').length,
      completed: list.filter((j) => j.status === 'completed').length,
      failed: list.filter((j) => j.status === 'failed').length,
      partial: list.filter((j) => j.status === 'partially_completed').length,
    };
  }, [jobs]);

  const filtered = useMemo(() => {
    const list = jobs || [];
    if (filter === 'all') return list;
    return list.filter((j) => j.status === filter);
  }, [jobs, filter]);

  const onRetry = async (id: string | number) => {
    if (typeof id === 'string' && id.startsWith('job-')) {
      setError('Retry is disabled for demo jobs.');
      return;
    }
    setRetrying(id);
    try {
      await retryJob(id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Retry failed');
    } finally {
      setRetrying(null);
    }
  };

  return (
    <div className="mx-auto max-w-[1400px] space-y-6 px-5 py-8">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <span className="chip-sky !text-[11px]">
            <span className="h-1.5 w-1.5 rounded-full bg-sky-400 animate-pulseSoft" />
            Distributed pipeline observability
          </span>
          <h1 className="mt-2 text-3xl font-extrabold tracking-tight md:text-4xl">Processing jobs</h1>
          <p className="mt-1 max-w-2xl text-sm text-white/60">
            Live operational view across the CineTag worker pipeline. Each job is an autoscaled,
            retryable task with stage-level instrumentation.
          </p>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-white/55">
          <span className="chip-neutral">auto-refresh 15s</span>
          <button onClick={load} className="btn-ghost !px-2.5 !py-1 !text-xs">
            Refresh
          </button>
        </div>
      </header>

      {error ? (
        <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-[12.5px] text-amber-200">
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <SummaryCard label="Total" value={summary.total} accent="white" />
        <SummaryCard label="Queued" value={summary.queued} accent="white" />
        <SummaryCard label="Running" value={summary.running} accent="sky" />
        <SummaryCard label="Completed" value={summary.completed} accent="emerald" />
        <SummaryCard label="Partial" value={summary.partial} accent="amber" />
        <SummaryCard label="Failed" value={summary.failed} accent="rose" />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={[
              'rounded-full border px-3 py-1 text-[11.5px] capitalize transition',
              filter === f
                ? 'border-cinetag-red/50 bg-cinetag-red/15 text-cinetag-redGlow'
                : 'border-white/10 bg-white/5 text-white/65 hover:bg-white/10',
            ].join(' ')}
          >
            {f.replace('_', ' ')}
          </button>
        ))}
      </div>

      {!jobs ? (
        <div className="panel p-6 text-sm text-white/55">Loading jobs…</div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No jobs match your filter"
          description="Try a different status filter or upload a new video to spin up a fresh job."
          action={{ label: 'Upload video', href: '/upload' }}
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-cinetag-border/70">
          <table className="hidden w-full text-[12.5px] md:table">
            <thead className="bg-cinetag-panelMuted/60 text-[11px] uppercase tracking-wider text-white/50">
              <tr>
                <th className="px-4 py-3 text-left">Job</th>
                <th className="px-4 py-3 text-left">Video</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Stage</th>
                <th className="px-4 py-3 text-left">Retries</th>
                <th className="px-4 py-3 text-left">Created</th>
                <th className="px-4 py-3 text-left">Started</th>
                <th className="px-4 py-3 text-left">Completed</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cinetag-border/60 bg-cinetag-panel/60">
              {filtered.map((j) => (
                <tr key={String(j.id)} className="hover:bg-white/[0.03]">
                  <td className="px-4 py-3 font-mono text-white/90">#{j.id}</td>
                  <td className="px-4 py-3">
                    {j.video_id != null ? (
                      <Link href={`/videos/${j.video_id}`} className="text-white hover:text-cinetag-redGlow">
                        {j.video_title || `Video #${j.video_id}`}
                      </Link>
                    ) : (
                      <span className="text-white/55">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <JobStatusBadge status={j.status} compact />
                  </td>
                  <td className="px-4 py-3">
                    <JobStatusBadge stage={j.current_stage} compact />
                  </td>
                  <td className="px-4 py-3 font-mono">{j.retry_count ?? 0}</td>
                  <td className="px-4 py-3 text-white/65">{formatRelativeTime(j.created_at)}</td>
                  <td className="px-4 py-3 text-white/65">{formatRelativeTime(j.started_at)}</td>
                  <td className="px-4 py-3 text-white/65">{formatRelativeTime(j.completed_at)}</td>
                  <td className="px-4 py-3 text-right">
                    {j.status === 'failed' || j.status === 'partially_completed' ? (
                      <button
                        onClick={() => onRetry(j.id)}
                        disabled={retrying === j.id}
                        className="btn !px-2.5 !py-1 !text-[11px] bg-white/5 ring-1 ring-white/10 hover:bg-white/10"
                      >
                        {retrying === j.id ? 'Retrying…' : 'Retry'}
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <ul className="md:hidden">
            {filtered.map((j) => (
              <li key={String(j.id)} className="border-b border-cinetag-border/60 bg-cinetag-panel/60 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-mono text-[12px] text-white/85">#{j.id}</div>
                    <div className="mt-0.5 text-sm font-semibold text-white">
                      {j.video_title || `Video #${j.video_id}`}
                    </div>
                  </div>
                  <JobStatusBadge status={j.status} compact />
                </div>
                {j.error_message ? (
                  <div className="mt-2 rounded-md border border-rose-500/40 bg-rose-500/10 px-2.5 py-1.5 text-[11.5px] text-rose-100">
                    {j.error_message}
                  </div>
                ) : null}
                <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] text-white/65">
                  <div>
                    stage: <JobStatusBadge stage={j.current_stage} compact />
                  </div>
                  <div>retries: {j.retry_count ?? 0}</div>
                  <div>created: {formatRelativeTime(j.created_at)}</div>
                  <div>completed: {formatRelativeTime(j.completed_at)}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {usedDemo ? (
        <div className="rounded-md border border-cinetag-border/70 bg-cinetag-panelMuted/60 px-3 py-2 text-[12px] text-white/55">
          No live jobs found — showing demo jobs to illustrate the dashboard.
        </div>
      ) : null}

      <section className="mx-auto max-w-[1400px] space-y-3 px-0">
        <PipelineFlow />
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Note title="Worker autoscaling">
            Workers consume from a Redis-backed queue. Cloud Run scales replicas on queue depth and CPU.
          </Note>
          <Note title="Stage-level retries">
            Each stage is independently retryable; failed stages mark the job partially_completed.
          </Note>
          <Note title="Observability">
            Stage durations and counters are exported to Prometheus and Cloud Monitoring.
          </Note>
        </div>
      </section>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent: 'white' | 'sky' | 'emerald' | 'amber' | 'rose';
}) {
  const ring: Record<string, string> = {
    white: 'ring-white/10',
    sky: 'ring-sky-400/30',
    emerald: 'ring-emerald-400/30',
    amber: 'ring-amber-400/30',
    rose: 'ring-rose-400/30',
  };
  const text: Record<string, string> = {
    white: 'text-white',
    sky: 'text-sky-300',
    emerald: 'text-emerald-300',
    amber: 'text-amber-300',
    rose: 'text-rose-300',
  };
  return (
    <div className={`panel p-4 ring-1 ${ring[accent]}`}>
      <div className="text-[11px] uppercase tracking-wider text-white/50">{label}</div>
      <div className={`mt-1 text-2xl font-extrabold ${text[accent]}`}>{value}</div>
    </div>
  );
}

function Note({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="panel p-4">
      <div className="text-[11px] uppercase tracking-wider text-white/50">{title}</div>
      <div className="mt-1 text-[12.5px] text-white/70">{children}</div>
    </div>
  );
}
