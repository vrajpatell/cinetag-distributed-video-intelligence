import { PIPELINE_STAGES } from '@/lib/demo-data';

export default function PipelineFlow({
  activeStage,
  compact = false,
}: {
  activeStage?: string;
  compact?: boolean;
}) {
  const activeIdx = PIPELINE_STAGES.findIndex((s) => s.key === activeStage);
  return (
    <section className="mx-auto w-full max-w-[1400px] px-5">
      <div className={`panel-strong relative overflow-hidden ${compact ? 'p-5' : 'p-6 md:p-8'}`}>
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
        {!compact ? (
          <div className="mb-6 flex flex-col gap-1 md:flex-row md:items-end md:justify-between">
            <div>
              <div className="text-[11px] uppercase tracking-wider text-white/50">
                The CineTag pipeline
              </div>
              <h2 className="mt-1 text-2xl font-bold tracking-tight">
                Upload &rarr; Tagged metadata &rarr; Discovery
              </h2>
              <p className="mt-1 max-w-2xl text-sm text-white/55">
                Each stage is an independently retryable worker step. Backpressure is managed by
                Redis-backed Celery queues; results are persisted to Cloud SQL with audit logs.
              </p>
            </div>
            <div className="flex items-center gap-2 text-[11px] text-white/55">
              <span className="chip-neutral">async</span>
              <span className="chip-neutral">retryable</span>
              <span className="chip-neutral">observable</span>
            </div>
          </div>
        ) : null}

        <ol className="relative grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-9">
          {PIPELINE_STAGES.map((s, i) => {
            const state =
              activeIdx === -1
                ? 'idle'
                : i < activeIdx
                  ? 'done'
                  : i === activeIdx
                    ? 'active'
                    : 'pending';
            const dot =
              state === 'done'
                ? 'bg-emerald-400'
                : state === 'active'
                  ? 'bg-cinetag-redGlow animate-pulseSoft'
                  : 'bg-white/20';
            const ring =
              state === 'done'
                ? 'ring-emerald-400/30'
                : state === 'active'
                  ? 'ring-cinetag-red/40'
                  : 'ring-white/10';
            const text =
              state === 'pending' ? 'text-white/55' : 'text-white';
            return (
              <li key={s.key} className={`relative panel-muted px-3 py-3 ring-1 ${ring}`}>
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${dot}`} />
                  <span className="text-[10px] uppercase tracking-wider text-white/45">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                </div>
                <div className={`mt-1 text-[12.5px] font-semibold ${text}`}>{s.label}</div>
                <div className="mt-0.5 line-clamp-2 text-[10.5px] text-white/45">
                  {s.description}
                </div>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
