import { STAGE_LABELS, type UploadProgressInfo, type UploadStage } from '@/lib/upload';
import { formatBitsPerSecond, formatBytes, formatDuration, clamp } from '@/lib/format';

const ORDER: UploadStage[] = [
  'preparing_signed_upload',
  'uploading_to_cloud_storage',
  'finalizing_upload',
  'creating_processing_job',
  'queued_for_analysis',
];

export default function UploadProgress({
  stage,
  progress,
}: {
  stage: UploadStage | null;
  progress: UploadProgressInfo | null;
}) {
  if (!stage) return null;
  const idx = stage === 'failed' ? -1 : ORDER.indexOf(stage);
  const pct = clamp(progress?.percent ?? 0, 0, 100);

  return (
    <div className="panel-strong overflow-hidden">
      <div className="flex flex-col gap-1 border-b border-cinetag-border/70 px-5 py-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-2">
          <span
            className={[
              'inline-flex h-2 w-2 rounded-full',
              stage === 'failed'
                ? 'bg-rose-400'
                : stage === 'queued_for_analysis'
                  ? 'bg-emerald-400'
                  : 'bg-cinetag-redGlow animate-pulseSoft',
            ].join(' ')}
          />
          <span className="text-sm font-semibold text-white">
            {stage === 'failed' ? 'Upload failed' : STAGE_LABELS[stage]}
          </span>
        </div>
        {stage === 'uploading_to_cloud_storage' && progress ? (
          <div className="flex items-center gap-3 font-mono text-[11px] text-white/70">
            <span>{pct.toFixed(1)}%</span>
            <span className="text-white/30">|</span>
            <span>
              {formatBytes(progress.bytesUploaded)} / {formatBytes(progress.bytesTotal)}
            </span>
            <span className="text-white/30">|</span>
            <span>{formatBitsPerSecond(progress.speedBytesPerSec)}</span>
            <span className="text-white/30">|</span>
            <span>ETA {formatDuration(progress.etaSeconds)}</span>
          </div>
        ) : null}
      </div>

      {stage === 'uploading_to_cloud_storage' ? (
        <div className="px-5 pt-4">
          <div className="relative h-2 w-full overflow-hidden rounded-full bg-white/5">
            <div
              className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-cinetag-red to-cinetag-redGlow shadow-glow transition-[width] duration-200"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      ) : null}

      <ol className="grid grid-cols-1 gap-2 px-5 py-4 sm:grid-cols-2 md:grid-cols-5">
        {ORDER.map((s, i) => {
          const state =
            stage === 'failed'
              ? i === 0
                ? 'failed'
                : 'pending'
              : i < idx
                ? 'done'
                : i === idx
                  ? 'active'
                  : 'pending';
          const dot =
            state === 'done'
              ? 'bg-emerald-400'
              : state === 'active'
                ? 'bg-cinetag-redGlow animate-pulseSoft'
                : state === 'failed'
                  ? 'bg-rose-400'
                  : 'bg-white/20';
          const text =
            state === 'pending' ? 'text-white/55' : state === 'failed' ? 'text-rose-200' : 'text-white';
          return (
            <li key={s} className="panel-muted px-3 py-2.5">
              <div className="flex items-center gap-2">
                <span className={`h-2 w-2 rounded-full ${dot}`} />
                <span className="text-[10px] uppercase tracking-wider text-white/45">
                  {String(i + 1).padStart(2, '0')}
                </span>
              </div>
              <div className={`mt-1 text-[12.5px] font-semibold ${text}`}>{STAGE_LABELS[s]}</div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
