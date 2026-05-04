import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight, RefreshCw } from 'lucide-react';
import { Badge, jobStatusTone } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/Button';
import { useJobs } from '@/state/hooks/useJobs';
import { useVideos } from '@/state/hooks/useVideos';
import { formatRelative, humanizeDuration } from '@/lib/format';
import type { ProcessingJob, VideoAsset } from '@/lib/zodSchemas';

const STATUSES: Array<ProcessingJob['status'] | 'all'> = [
  'all',
  'queued',
  'running',
  'succeeded',
  'failed',
  'cancelled',
];

export default function JobsPage(): JSX.Element {
  const jobsQ = useJobs();
  const videosQ = useVideos();
  const [filter, setFilter] = useState<(typeof STATUSES)[number]>('all');

  const videosById = useMemo(() => {
    const map = new Map<number, VideoAsset>();
    for (const v of videosQ.data ?? []) map.set(v.id, v);
    return map;
  }, [videosQ.data]);

  const counts = useMemo(() => {
    const out: Record<string, number> = { all: 0 };
    for (const j of jobsQ.data ?? []) {
      out.all = (out.all ?? 0) + 1;
      out[j.status] = (out[j.status] ?? 0) + 1;
    }
    return out;
  }, [jobsQ.data]);

  const filtered = useMemo(() => {
    const list = jobsQ.data ?? [];
    const sorted = [...list].sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
    if (filter === 'all') return sorted;
    return sorted.filter((j) => j.status === filter);
  }, [jobsQ.data, filter]);

  return (
    <div className="mx-auto max-w-rail px-4 pb-16 pt-8 sm:px-6 lg:px-12">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold tracking-tightest text-text-0 sm:text-4xl">
            Jobs
          </h1>
          <p className="mt-1 text-sm text-text-1">
            Pipeline runs auto-refresh every 5 seconds while any are queued or running.
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => jobsQ.refetch()}
          loading={jobsQ.isFetching}
          iconLeft={!jobsQ.isFetching ? <RefreshCw className="h-4 w-4" aria-hidden /> : undefined}
        >
          Refresh
        </Button>
      </header>

      <div className="mt-6 flex flex-wrap gap-2">
        {STATUSES.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setFilter(s)}
            className={`rounded-full border px-3 py-1 text-xs font-medium tracking-tight transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
              filter === s
                ? 'border-accent bg-accent text-white'
                : 'border-bg-3 bg-bg-1 text-text-1 hover:bg-bg-2 hover:text-text-0'
            }`}
          >
            <span className="capitalize">{s}</span>
            <span className="ml-1.5 text-[10px] opacity-70">{counts[s] ?? 0}</span>
          </button>
        ))}
      </div>

      <section className="mt-6 overflow-hidden rounded-lg border border-bg-3 bg-bg-1">
        <div className="hidden grid-cols-[80px_1fr_120px_140px_140px_140px_24px] gap-4 border-b border-bg-3 px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.15em] text-text-2 sm:grid">
          <span>Job</span>
          <span>Video</span>
          <span>Status</span>
          <span>Stage</span>
          <span>Started</span>
          <span>Retries</span>
          <span aria-hidden />
        </div>
        {jobsQ.isLoading ? (
          <ul>
            {Array.from({ length: 6 }).map((_, i) => (
              <li key={i} className="border-t border-bg-3 px-4 py-4">
                <Skeleton className="h-6 w-full" />
              </li>
            ))}
          </ul>
        ) : jobsQ.isError ? (
          <p role="alert" className="px-4 py-8 text-center text-sm text-accent">
            Failed to load jobs: {(jobsQ.error as Error).message}
          </p>
        ) : filtered.length === 0 ? (
          <p className="px-4 py-12 text-center text-sm text-text-2">No jobs match this filter.</p>
        ) : (
          <ul>
            {filtered.map((job) => {
              const video = videosById.get(job.video_id);
              return (
                <li key={job.id} className="border-t border-bg-3 transition-colors hover:bg-bg-2">
                  <Link
                    to={`/jobs/${job.id}`}
                    className="grid grid-cols-1 items-center gap-2 px-4 py-3 text-sm sm:grid-cols-[80px_1fr_120px_140px_140px_140px_24px] sm:gap-4"
                  >
                    <span className="font-mono text-text-0">#{job.id}</span>
                    <span className="truncate">
                      <span className="font-medium text-text-0">
                        {video ? video.title ?? video.original_filename : `Video #${job.video_id}`}
                      </span>
                      {video?.duration_seconds != null && (
                        <span className="ml-2 text-xs text-text-2">
                          {humanizeDuration(video.duration_seconds)}
                        </span>
                      )}
                    </span>
                    <span>
                      <Badge tone={jobStatusTone(job.status)}>
                        <span className="capitalize">{job.status}</span>
                      </Badge>
                    </span>
                    <span className="truncate text-text-1">{job.current_stage ?? '—'}</span>
                    <span className="text-text-1">{formatRelative(job.started_at ?? job.created_at)}</span>
                    <span className="text-text-1">×{job.retry_count}</span>
                    <ChevronRight className="hidden h-4 w-4 text-text-2 sm:inline" aria-hidden />
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
