import { API_BASE_URL } from '@/lib/api';

export default function FooterDebug() {
  const env = process.env.NEXT_PUBLIC_APP_ENV || process.env.NODE_ENV || 'dev';
  const build = process.env.NEXT_PUBLIC_BUILD_VERSION || 'dev';
  const region = process.env.NEXT_PUBLIC_GCP_REGION || 'us-central1';
  const apiLabel = API_BASE_URL || 'unset';
  return (
    <footer className="mt-16 border-t border-cinetag-border/70 bg-cinetag-ink/60">
      <div className="mx-auto max-w-[1400px] px-5 py-6 text-[12px] text-white/55">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <span className="inline-flex items-center gap-2 font-semibold text-white/80">
              <span className="grid h-5 w-5 place-items-center rounded bg-cinetag-red/90 ring-1 ring-white/10">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path d="M5 7h14M5 12h10M5 17h12" stroke="white" strokeWidth="2.4" strokeLinecap="round" />
                </svg>
              </span>
              CineTag
            </span>
            <span className="text-white/40">·</span>
            <span>AI-powered video intelligence for streaming platforms.</span>
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono">
            <span><span className="text-white/40">env</span> {env}</span>
            <span className="text-white/30">|</span>
            <span><span className="text-white/40">api</span> {apiLabel}</span>
            <span className="text-white/30">|</span>
            <span><span className="text-white/40">build</span> {build}</span>
            <span className="text-white/30">|</span>
            <span><span className="text-white/40">deploy</span> GCP · {region}</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
