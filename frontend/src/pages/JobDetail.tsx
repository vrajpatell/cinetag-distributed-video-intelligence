import { Link, useParams } from 'react-router-dom';
import { AlertTriangle, ChevronLeft, RefreshCw } from 'lucide-react';
import { Badge, jobStatusTone } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { Card } from '@/components/ui/Card';
import { useJob, useRetryJob } from '@/state/hooks/useJobs';
import { useVideo } from '@/state/hooks/useVideos';
import {
  PipelineStepper,
  deriveStepsFromJob,
} from '@/components/media/PipelineStepper';
import { PosterFallback } from '@/components/media/MediaCard';
import { formatRelative, humanizeDuration } from '@/lib/format';

export default function JobDetailPage(): JSX.Element {
  const { id } = useParams<{ id: string }>();
  const jobQ = useJob(id);
  const videoQ = useVideo(jobQ.data?.video_id);
  const retry = useRetryJob(jobQ.data?.id);

  if (jobQ.isLoading) {
    return (
      <div className="mx-auto max-w-rail px-4 py-8 sm:px-6 lg:px-12">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="mt-6 h-32 w-full" />
        <Skeleton className="mt-6 h-96 w-full" />
      </div>
    );
  }

  if (jobQ.isError || !jobQ.data) {
    return (
      <div className="mx-auto max-w-rail px-4 py-16 text-center sm:px-6 lg:px-12">
        <p className="font-display text-2xl font-bold text-text-0">Job not found</p>
        <p className="mt-2 text-sm text-text-1">{(jobQ.error as Error)?.message ?? `No job with id ${id}.`}</p>
        <Link to="/jobs" className="mt-4 inline-block">
          <Button variant="ghost" iconLeft={<ChevronLeft className="h-4 w-4" aria-hidden />}>
            Back to jobs
          </Button>
        </Link>
      </div>
    );
  }

  const job = jobQ.data;
  const video = videoQ.data;
  const steps = deriveStepsFromJob(job.current_stage, job.status);
  const failed = job.status === 'failed';

  return (
    <div className="mx-auto max-w-rail px-4 py-8 sm:px-6 lg:px-12">
      <Link
        to="/jobs"
        className="inline-flex items-center gap-1 text-sm text-text-1 hover:text-text-0"
      >
        <ChevronLeft className="h-4 w-4" aria-hidden /> All jobs
      </Link>

      <header className="mt-4 flex flex-wrap items-center gap-6">
        <div className="relative h-[100px] w-[178px] shrink-0 overflow-hidden rounded-md border border-bg-3 bg-bg-2">
          {video ? (
            <PosterFallback
              title={video.title ?? video.original_filename}
              videoId={video.id}
            />
          ) : (
            <Skeleton className="h-full w-full rounded-none" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-mono text-text-2">JOB #{job.id}</p>
          <h1 className="line-clamp-2 font-display text-2xl font-bold tracking-tightest text-text-0 sm:text-3xl">
            {video ? video.title ?? video.original_filename : `Video #${job.video_id}`}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-text-1">
            <Badge tone={jobStatusTone(job.status)}>
              <span className="capitalize">{job.status}</span>
            </Badge>
            <span>Stage: {job.current_stage ?? '—'}</span>
            <span>·</span>
            <span>Created {formatRelative(job.created_at)}</span>
            {video?.duration_seconds != null && (
              <>
                <span>·</span>
                <span>{humanizeDuration(video.duration_seconds)}</span>
              </>
            )}
            <span>·</span>
            <span>{job.retry_count} retries</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {video && (
            <Link to={`/videos/${video.id}`}>
              <Button variant="ghost">View video</Button>
            </Link>
          )}
          <Button
            variant="primary"
            onClick={() => retry.mutate()}
            loading={retry.isPending}
            iconLeft={!retry.isPending ? <RefreshCw className="h-4 w-4" aria-hidden /> : undefined}
          >
            Retry
          </Button>
        </div>
      </header>

      {failed && job.error_message && (
        <div
          role="alert"
          className="mt-6 flex items-start gap-3 rounded-md border border-accent/40 bg-accent/10 p-4 text-sm text-accent"
        >
          <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0" aria-hidden />
          <div>
            <p className="font-semibold">Pipeline failed</p>
            <p className="mt-1 whitespace-pre-wrap break-words text-accent/90">{job.error_message}</p>
          </div>
        </div>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Card className="p-6">
          <h2 className="font-display text-lg font-semibold tracking-tight text-text-0">Pipeline</h2>
          <p className="mt-1 text-xs text-text-2">
            Derived from <code className="font-mono">current_stage</code>. Per-stage durations will populate
            once stage-run telemetry is wired through the API.
          </p>
          <div className="mt-5">
            <PipelineStepper steps={steps} />
          </div>
        </Card>
        <Card className="p-6">
          <h2 className="font-display text-lg font-semibold tracking-tight text-text-0">Timeline</h2>
          <dl className="mt-4 space-y-3 text-sm">
            <Row label="Created" value={new Date(job.created_at).toLocaleString()} />
            <Row label="Updated" value={new Date(job.updated_at).toLocaleString()} />
            <Row label="Started" value={job.started_at ? new Date(job.started_at).toLocaleString() : '—'} />
            <Row label="Completed" value={job.completed_at ? new Date(job.completed_at).toLocaleString() : '—'} />
            <Row label="Retries" value={String(job.retry_count)} />
          </dl>
        </Card>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-xs uppercase tracking-wider text-text-2">{label}</dt>
      <dd className="text-text-0">{value}</dd>
    </div>
  );
}
