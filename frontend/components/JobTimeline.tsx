import { PIPELINE_STAGES } from '@/lib/demo-data';
import { formatRelativeTime } from '@/lib/format';
import type { JobSummary } from '@/lib/types';

export default function JobTimeline({ job }: { job: JobSummary }) {
  const activeIdx = PIPELINE_STAGES.findIndex((s) => s.key === job.current_stage);
  const isFailed = job.status === 'failed';
  const isCompleted = job.status === 'completed';
  const events = [
    { label: 'created', value: job.created_at },
    { label: 'started', value: job.started_at },
    { label: 'completed', value: job.completed_at },
  ];
  return (
    <div className="panel p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-white/50">Processing timeline</div>
          <div className="text-base font-semibold text-white">Job #{job.id}</div>
        </div>
        <div className="flex flex-wrap gap-3 text-[11px] text-white/55">
          {events
            .filter((e) => e.value)
            .map((e) => (
              <div key={e.label} className="panel-muted px-2.5 py-1">
                <span className="text-white/45">{e.label}</span>{' '}
                <span className="text-white/85">{formatRelativeTime(e.value)}</span>
              </div>
            ))}
        </div>
      </div>

      <ol className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-9">
        {PIPELINE_STAGES.map((s, i) => {
          const state =
            isFailed && i === activeIdx
              ? 'failed'
              : isCompleted
                ? 'done'
                : activeIdx === -1
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
                : state === 'failed'
                  ? 'bg-rose-400'
                  : 'bg-white/20';
          return (
            <li key={s.key} className="panel-muted px-2.5 py-2">
              <div className="flex items-center gap-1.5">
                <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
                <span className="text-[9.5px] uppercase tracking-wider text-white/40">{String(i + 1).padStart(2, '0')}</span>
              </div>
              <div className="mt-0.5 text-[11.5px] font-semibold text-white/90">{s.label}</div>
            </li>
          );
        })}
      </ol>

      {job.error_message ? (
        <div className="mt-4 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-[12px] text-rose-200">
          <span className="font-mono text-[11px] text-rose-100/80">error</span> {job.error_message}
        </div>
      ) : null}
    </div>
  );
}
