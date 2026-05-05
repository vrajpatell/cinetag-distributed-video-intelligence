import { ARCHITECTURE_CARDS } from '@/lib/demo-data';

const accentMap: Record<string, { bar: string; text: string; ring: string }> = {
  red: { bar: 'bg-cinetag-red', text: 'text-cinetag-redGlow', ring: 'ring-cinetag-red/30' },
  sky: { bar: 'bg-sky-400', text: 'text-sky-300', ring: 'ring-sky-400/30' },
  emerald: { bar: 'bg-emerald-400', text: 'text-emerald-300', ring: 'ring-emerald-400/30' },
  amber: { bar: 'bg-amber-400', text: 'text-amber-300', ring: 'ring-amber-400/30' },
  violet: { bar: 'bg-violet-400', text: 'text-violet-300', ring: 'ring-violet-400/30' },
  rose: { bar: 'bg-rose-400', text: 'text-rose-300', ring: 'ring-rose-400/30' },
};

export default function ArchitecturePanel() {
  return (
    <section className="mx-auto w-full max-w-[1400px] px-5">
      <div className="mb-3 flex items-end justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-white/50">Engineering credibility</div>
          <h2 className="mt-1 text-xl font-bold tracking-tight">Cloud-native architecture</h2>
          <p className="mt-1 max-w-2xl text-sm text-white/55">
            Designed for streaming-platform scale: stateless services, autoscaling workers,
            managed datastores, and built-in observability across the pipeline.
          </p>
        </div>
        <span className="hidden md:inline-flex chip-neutral !text-[10.5px]">Google Cloud Platform</span>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        {ARCHITECTURE_CARDS.map((c) => {
          const a = accentMap[c.accent] || accentMap.red;
          return (
            <div key={c.name} className={`panel relative overflow-hidden p-4 ring-1 ${a.ring}`}>
              <div className={`absolute inset-x-0 top-0 h-[2px] ${a.bar}`} />
              <div className={`text-[11px] uppercase tracking-wider ${a.text}`}>service</div>
              <div className="mt-1 text-sm font-semibold text-white">{c.name}</div>
              <div className="mt-1 text-[12px] text-white/55">{c.role}</div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
