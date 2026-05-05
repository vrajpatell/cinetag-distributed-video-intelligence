'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { API_BASE_URL, getHealthSnapshot, type HealthSnapshot } from '@/lib/api';

const LINKS = [
  { href: '/', label: 'Browse' },
  { href: '/upload', label: 'Upload' },
  { href: '/jobs', label: 'Jobs' },
  { href: '/review', label: 'Review' },
  { href: '/search', label: 'Search' },
];

export default function TopNav() {
  const pathname = usePathname() || '/';
  const [open, setOpen] = useState(false);
  const [health, setHealth] = useState<HealthSnapshot>({ api: 'unknown', ready: 'unknown' });

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      const snap = await getHealthSnapshot();
      if (!cancelled) setHealth(snap);
    };
    tick();
    const id = setInterval(tick, 30_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const env = health.env || process.env.NEXT_PUBLIC_APP_ENV || process.env.NODE_ENV || 'dev';
  const docsUrl = API_BASE_URL ? `${API_BASE_URL}/docs` : '/docs';

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname === href || pathname.startsWith(`${href}/`);

  return (
    <header className="sticky top-0 z-40 border-b border-cinetag-border/80 bg-cinetag-ink/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-4 px-5 py-3">
        <div className="flex items-center gap-8">
          <Link href="/" className="group flex items-center gap-2.5">
            <span className="relative grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-cinetag-redGlow to-cinetag-redDark shadow-glow ring-1 ring-white/10">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path d="M5 7h14M5 12h10M5 17h12" stroke="white" strokeWidth="2.4" strokeLinecap="round" />
              </svg>
            </span>
            <span className="text-[17px] font-extrabold tracking-tight">
              Cine<span className="text-cinetag-redGlow">Tag</span>
            </span>
            <span className="hidden md:inline-flex chip-neutral text-[10px] uppercase tracking-wider !rounded-full !px-2 !py-0.5">
              video intelligence
            </span>
          </Link>
          <nav className="hidden md:flex items-center gap-1">
            {LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={[
                  'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                  isActive(l.href)
                    ? 'bg-white/8 text-white shadow-inner ring-1 ring-white/10'
                    : 'text-white/65 hover:text-white hover:bg-white/5',
                ].join(' ')}
              >
                {l.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-2">
          <SystemHealthIndicator health={health} />
          <span className="hidden lg:inline-flex chip-neutral !text-[10px] uppercase tracking-wider">
            <span className="text-white/50">env</span>
            <span className="text-white/90">{env}</span>
          </span>
          <a
            href={docsUrl}
            target="_blank"
            rel="noreferrer noopener"
            className="hidden md:inline-flex btn-ghost !px-3 !py-1.5 !text-xs"
          >
            API Docs
          </a>
          <Link href="/upload" className="hidden sm:inline-flex btn-primary !px-3 !py-1.5 !text-xs">
            Upload
          </Link>
          <button
            type="button"
            aria-label="Toggle navigation"
            onClick={() => setOpen((v) => !v)}
            className="md:hidden inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-white/5"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </div>
      </div>

      {open ? (
        <div className="md:hidden border-t border-cinetag-border/70 bg-cinetag-ink">
          <div className="mx-auto flex max-w-[1400px] flex-col gap-1 px-5 py-3">
            {LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                onClick={() => setOpen(false)}
                className={[
                  'rounded-md px-3 py-2 text-sm',
                  isActive(l.href) ? 'bg-white/10 text-white' : 'text-white/70 hover:bg-white/5 hover:text-white',
                ].join(' ')}
              >
                {l.label}
              </Link>
            ))}
            <a
              href={docsUrl}
              target="_blank"
              rel="noreferrer noopener"
              className="rounded-md px-3 py-2 text-sm text-white/70 hover:bg-white/5 hover:text-white"
            >
              API Docs
            </a>
          </div>
        </div>
      ) : null}
    </header>
  );
}

function SystemHealthIndicator({ health }: { health: HealthSnapshot }) {
  const overall: 'ok' | 'down' | 'unknown' =
    health.api === 'ok' && health.ready === 'ok'
      ? 'ok'
      : health.api === 'down' || health.ready === 'down'
        ? 'down'
        : 'unknown';
  const dot =
    overall === 'ok' ? 'bg-emerald-400' : overall === 'down' ? 'bg-rose-500' : 'bg-amber-400';
  const label =
    overall === 'ok' ? 'All systems' : overall === 'down' ? 'API offline' : 'Health unknown';
  return (
    <span className="hidden sm:inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[11px] text-white/70">
      <span className={`h-1.5 w-1.5 rounded-full ${dot} animate-pulseSoft`} />
      {label}
    </span>
  );
}
