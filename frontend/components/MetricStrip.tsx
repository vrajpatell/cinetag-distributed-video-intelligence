import type { PlatformMetric } from '@/lib/types';

const ACCENT: Record<NonNullable<PlatformMetric['accent']>, { ring: string; bar: string; text: string }> = {
  red: { ring: 'ring-cinetag-red/30', bar: 'bg-cinetag-red', text: 'text-cinetag-redGlow' },
  sky: { ring: 'ring-sky-400/30', bar: 'bg-sky-400', text: 'text-sky-300' },
  emerald: { ring: 'ring-emerald-400/30', bar: 'bg-emerald-400', text: 'text-emerald-300' },
  amber: { ring: 'ring-amber-400/30', bar: 'bg-amber-400', text: 'text-amber-300' },
  violet: { ring: 'ring-violet-400/30', bar: 'bg-violet-400', text: 'text-violet-300' },
  rose: { ring: 'ring-rose-400/30', bar: 'bg-rose-400', text: 'text-rose-300' },
};

export default function MetricStrip({ metrics }: { metrics: PlatformMetric[] }) {
  return (
    <section className="mx-auto max-w-[1400px] px-5">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {metrics.map((m) => {
          const c = ACCENT[m.accent || 'red'];
          return (
            <div
              key={m.label}
              className={`panel relative overflow-hidden px-4 py-4 ring-1 ${c.ring}`}
            >
              <div className={`absolute inset-x-0 top-0 h-[2px] ${c.bar} opacity-80`} />
              <div className="text-[11px] uppercase tracking-wider text-white/50">{m.label}</div>
              <div className="mt-1 text-2xl font-extrabold tracking-tight text-white">{m.value}</div>
              {m.trend ? <div className={`mt-0.5 text-[11px] ${c.text}`}>{m.trend}</div> : null}
              {m.hint ? <div className="mt-1 text-[11px] text-white/40">{m.hint}</div> : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}
