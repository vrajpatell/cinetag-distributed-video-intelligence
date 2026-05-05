'use client';

import Link from 'next/link';
import { useCallback, useRef, useState } from 'react';
import UploadDropzone from '@/components/UploadDropzone';
import UploadProgress from '@/components/UploadProgress';
import ErrorToast, { type ErrorDetail } from '@/components/ErrorToast';
import PipelineFlow from '@/components/PipelineFlow';
import {
  uploadVideoDirectToGcs,
  UploadError,
  type UploadProgressInfo,
  type UploadResult,
  type UploadStage,
} from '@/lib/upload';

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [stage, setStage] = useState<UploadStage | null>(null);
  const [progress, setProgress] = useState<UploadProgressInfo | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<ErrorDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(async () => {
    if (!file) return;
    setError(null);
    setResult(null);
    setProgress(null);
    setStage('preparing_signed_upload');
    setBusy(true);
    abortRef.current = new AbortController();
    try {
      const res = await uploadVideoDirectToGcs({
        file,
        title: title || undefined,
        signal: abortRef.current.signal,
        onStageChange: (s) => setStage(s),
        onProgress: (p) => setProgress(p),
      });
      setResult(res);
      setStage('queued_for_analysis');
    } catch (err) {
      if (err instanceof UploadError) {
        setError({
          title: err.message,
          message: stageMessage(err.stage),
          endpoint: err.endpoint,
          status: err.status,
          hint: err.hint || stageHint(err.stage),
        });
      } else {
        setError({
          title: 'Upload failed',
          message: err instanceof Error ? err.message : 'Unknown error',
        });
      }
      setStage('failed');
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }, [file, title]);

  const reset = () => {
    abortRef.current?.abort();
    setFile(null);
    setTitle('');
    setStage(null);
    setProgress(null);
    setResult(null);
    setError(null);
    setBusy(false);
  };

  return (
    <div className="mx-auto max-w-[1100px] space-y-6 px-5 py-8">
      <header className="space-y-2">
        <span className="chip-red !text-[11px]">
          <span className="h-1.5 w-1.5 rounded-full bg-cinetag-redGlow animate-pulseSoft" />
          Direct-to-GCS · signed PUT
        </span>
        <h1 className="text-3xl font-extrabold tracking-tight md:text-4xl">Upload a video</h1>
        <p className="max-w-2xl text-sm text-white/60">
          CineTag never proxies large files through the API. Files stream directly to Google Cloud
          Storage using a short-lived signed URL, then a worker job picks up the asset for tagging.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr,360px]">
        <div className="space-y-5">
          <div className="panel-strong p-5">
            <UploadDropzone file={file} onFile={setFile} disabled={busy} maxSizeMb={5_000} />
            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
              <label className="block">
                <div className="mb-1 text-[11px] uppercase tracking-wider text-white/55">Title (optional)</div>
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  disabled={busy}
                  placeholder="e.g. Urban Chase Sequence"
                  className="w-full rounded-md border border-cinetag-border bg-cinetag-panelMuted/80 px-3 py-2 text-sm outline-none focus:border-cinetag-red/60"
                />
              </label>
              <div className="panel-muted px-3 py-2.5 text-[11.5px] text-white/65">
                <div className="text-white/50">Why direct upload?</div>
                <div className="mt-0.5">
                  Avoids API egress, supports multi-GB videos, frees API replicas for control-plane
                  traffic, and gives reliable progress on poor networks.
                </div>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <button onClick={start} disabled={!file || busy} className="btn-primary">
                {busy ? 'Uploading…' : 'Start upload'}
              </button>
              {busy ? (
                <button onClick={reset} className="btn-secondary">
                  Cancel
                </button>
              ) : (
                <button onClick={reset} className="btn-ghost">
                  Reset
                </button>
              )}
              <span className="ml-auto text-[11px] text-white/45">
                Accepted: <span className="font-mono">.mp4</span> ·{' '}
                <span className="font-mono">.mov</span> · <span className="font-mono">.mkv</span>
              </span>
            </div>
          </div>

          <UploadProgress stage={stage} progress={progress} />

          <ErrorToast error={error} onDismiss={() => setError(null)} onRetry={start} />

          {result ? <UploadSuccess result={result} /> : null}
        </div>

        <aside className="space-y-4">
          <SidePanel
            title="What happens next?"
            items={[
              ['Init', 'POST /api/uploads/init reserves a video row and returns a signed GCS URL.'],
              ['PUT', 'Browser streams the file directly to Cloud Storage with progress events.'],
              ['Complete', 'POST /api/uploads/complete confirms the object and creates a job.'],
              ['Pipeline', 'Worker runs metadata, frames, transcript, tags, and embeddings.'],
            ]}
          />
          <SidePanel
            title="Production tips"
            items={[
              ['CORS', 'Allow PUT from your frontend origin on the GCS bucket.'],
              ['IAM', 'Cloud Run service account needs roles/iam.serviceAccountTokenCreator.'],
              ['Lifecycle', 'Add a 7-day delete rule for upload_pending/ to clean orphans.'],
              ['Limits', 'Worker autoscales on queue depth; tune max concurrency per asset.'],
            ]}
          />
        </aside>
      </div>

      <PipelineFlow activeStage={mapStageToPipeline(stage)} compact />
    </div>
  );
}

function SidePanel({ title, items }: { title: string; items: [string, string][] }) {
  return (
    <div className="panel p-4">
      <div className="text-[11px] uppercase tracking-wider text-white/50">{title}</div>
      <ul className="mt-2 space-y-2.5 text-[12.5px]">
        {items.map(([k, v]) => (
          <li key={k} className="flex gap-2">
            <span className="mt-0.5 inline-flex h-5 min-w-12 shrink-0 items-center justify-center rounded bg-cinetag-red/15 px-1.5 font-mono text-[10px] uppercase tracking-wider text-cinetag-redGlow">
              {k}
            </span>
            <span className="text-white/70">{v}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function UploadSuccess({ result }: { result: UploadResult }) {
  return (
    <div className="panel-strong relative overflow-hidden p-5">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-400/60 to-transparent" />
      <div className="flex items-center gap-2">
        <span className="grid h-7 w-7 place-items-center rounded-full bg-emerald-500/20 ring-1 ring-emerald-400/40">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
            <path d="m5 12 5 5 9-11" stroke="rgb(110, 231, 183)" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
        <h3 className="text-base font-semibold text-white">Queued for analysis</h3>
      </div>
      <p className="mt-1 text-[12.5px] text-white/65">
        Your video is now in Cloud Storage and a processing job has been enqueued.
      </p>
      <dl className="mt-4 grid grid-cols-1 gap-2 md:grid-cols-3">
        <Field k="video_id" v={String(result.video_id)} />
        <Field k="job_id" v={String(result.job_id)} />
        <Field k="status" v={result.status} />
      </dl>
      <div className="mt-2">
        <Field k="storage_key" v={result.storage_key} mono />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Link href={`/jobs`} className="btn-secondary">
          Open job dashboard
        </Link>
        <Link href={`/videos/${result.video_id}`} className="btn-primary">
          View video detail
        </Link>
      </div>
    </div>
  );
}

function Field({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="panel-muted px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-white/45">{k}</div>
      <div className={`mt-0.5 truncate text-[12.5px] text-white/90 ${mono ? 'font-mono' : ''}`}>{v}</div>
    </div>
  );
}

function stageMessage(stage: UploadStage): string {
  switch (stage) {
    case 'preparing_signed_upload':
      return 'The API could not return a signed upload URL.';
    case 'uploading_to_cloud_storage':
      return 'Cloud Storage rejected the file transfer.';
    case 'creating_processing_job':
      return 'The video reached storage but the worker job could not be enqueued.';
    default:
      return 'The upload pipeline failed.';
  }
}

function stageHint(stage: UploadStage): string {
  switch (stage) {
    case 'preparing_signed_upload':
      return 'Check NEXT_PUBLIC_API_BASE_URL and that POST /api/uploads/init is reachable.';
    case 'uploading_to_cloud_storage':
      return 'Verify GCS bucket CORS allows PUT from this origin, and the SA can sign URLs.';
    case 'creating_processing_job':
      return 'Make sure the worker is online and POST /api/uploads/complete responds.';
    default:
      return 'Try again, or check the API logs.';
  }
}

function mapStageToPipeline(stage: UploadStage | null): string | undefined {
  if (!stage) return undefined;
  if (stage === 'queued_for_analysis') return 'queued';
  return 'queued';
}
