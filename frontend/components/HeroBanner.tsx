import Link from 'next/link';

export default function HeroBanner() {
  return (
    <section className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 grid-bg opacity-[0.35]" />
      <div className="pointer-events-none absolute -top-24 left-1/2 h-[440px] w-[80vw] -translate-x-1/2 rounded-[100%] bg-cinetag-red/20 blur-[120px]" />
      <div className="pointer-events-none absolute -bottom-32 right-0 h-[320px] w-[60vw] rounded-[100%] bg-violet-500/15 blur-[120px]" />
      <div className="relative mx-auto grid max-w-[1400px] grid-cols-1 gap-10 px-5 py-14 lg:grid-cols-12 lg:gap-12 lg:py-20">
        <div className="lg:col-span-7">
          <span className="chip-red mb-5 !rounded-full !px-3 !py-1 !text-[11px]">
            <span className="h-1.5 w-1.5 rounded-full bg-cinetag-redGlow animate-pulseSoft" />
            Distributed video intelligence platform
          </span>
          <h1 className="text-balance text-[clamp(2.4rem,5vw,4.4rem)] font-extrabold leading-[1.05] tracking-tight">
            <span className="text-gradient-cool">CineTag</span>{' '}
            <span className="text-gradient-red">Pipeline</span>
          </h1>
          <p className="mt-5 max-w-2xl text-balance text-base leading-relaxed text-white/75 md:text-lg">
            Distributed video intelligence for tagging, discovery, and recommendation-ready metadata.
            Ingest assets at scale, run them through autoscaled GPU/CPU workers, and turn raw video
            into structured, searchable content for streaming-platform experiences.
          </p>
          <div className="mt-7 flex flex-wrap items-center gap-3">
            <Link href="/upload" className="btn-primary">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path d="M12 4v12m0-12-4 4m4-4 4 4M5 20h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Upload Video
            </Link>
            <Link href="/jobs" className="btn-secondary">
              Explore Jobs
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path d="M5 12h14m0 0-5-5m5 5-5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </Link>
            <Link href="/search" className="btn-ghost">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
                <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
                <path d="m20 20-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              Search Content
            </Link>
            <a
              href={(process.env.NEXT_PUBLIC_API_BASE_URL || '').replace(/\/+$/, '') + '/docs' || '/docs'}
              target="_blank"
              rel="noreferrer noopener"
              className="btn-ghost"
            >
              Open API Docs
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path d="M14 4h6v6m0-6L10 14M9 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </a>
          </div>
          <ul className="mt-9 grid grid-cols-3 gap-4 text-[12px] text-white/60">
            {[
              { label: 'Ingestion', sub: 'Direct-to-GCS' },
              { label: 'AI Tagging', sub: 'LLM + multimodal' },
              { label: 'Discovery', sub: 'Semantic search' },
            ].map((p) => (
              <li key={p.label} className="panel-muted px-3 py-2.5">
                <div className="text-white/85 text-[13px] font-semibold">{p.label}</div>
                <div className="text-white/50">{p.sub}</div>
              </li>
            ))}
          </ul>
        </div>

        <div className="lg:col-span-5">
          <FeaturedIntelligenceCard />
        </div>
      </div>
    </section>
  );
}

function FeaturedIntelligenceCard() {
  return (
    <div className="panel-strong noise relative overflow-hidden p-5">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cinetag-redGlow/60 to-transparent" />
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-white/50">Featured asset</div>
          <div className="mt-1 text-base font-semibold text-white">Urban Chase Sequence</div>
          <div className="text-xs text-white/55">4K · 23.976 fps · h264 · 4m 18s</div>
        </div>
        <span className="chip-emerald">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulseSoft" />
          review_ready
        </span>
      </div>

      <div className="relative mt-4 aspect-video w-full overflow-hidden rounded-lg bg-thumb-1">
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/0 to-black/30" />
        <div className="absolute left-3 top-3 flex items-center gap-1.5">
          <span className="chip-red !text-[10px]">action</span>
          <span className="chip-neutral !text-[10px]">tension</span>
        </div>
        <div className="absolute bottom-3 left-3 right-3 flex items-end justify-between text-[11px] text-white/85">
          <div className="font-mono">
            <span className="text-white/50">latency</span> 1m 42s
          </div>
          <div className="font-mono">
            <span className="text-white/50">conf</span> 0.91
          </div>
        </div>
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -inset-x-full top-0 h-full w-[40%] bg-gradient-to-r from-transparent via-white/10 to-transparent animate-scanline" />
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 text-[11px]">
        <div className="panel-muted px-3 py-2">
          <div className="text-white/50">Stage</div>
          <div className="mt-0.5 text-white/90">llm_tagging → review</div>
        </div>
        <div className="panel-muted px-3 py-2">
          <div className="text-white/50">Worker</div>
          <div className="mt-0.5 text-white/90">cinetag-worker · run-7af</div>
        </div>
      </div>

      <div className="mt-4">
        <div className="mb-2 text-[11px] uppercase tracking-wider text-white/50">AI tags</div>
        <div className="flex flex-wrap gap-1.5">
          {[
            { v: 'action', t: 'genre', c: 0.94 },
            { v: 'tension', t: 'mood', c: 0.88 },
            { v: 'rooftop', t: 'scene', c: 0.82 },
            { v: 'car', t: 'object', c: 0.91 },
            { v: 'pursuit', t: 'theme', c: 0.76 },
          ].map((t) => (
            <span key={t.v} className="chip-neutral">
              {t.v}
              <span className="text-white/40">·</span>
              <span className="font-mono text-white/60">{t.c.toFixed(2)}</span>
            </span>
          ))}
        </div>
      </div>

      <div className="mt-4 panel-muted px-3 py-2.5 text-[11px] text-white/70">
        <span className="text-white/50">Recommend reason:</span> Strong overlap with “fast-paced urban
        thrillers” cluster (top decile).
      </div>
    </div>
  );
}
