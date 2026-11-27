'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  Clapperboard,
  Library,
  ExternalLink,
  Menu,
  Search,
  Upload,
  Workflow,
  ClipboardCheck,
  Home,
} from 'lucide-react';
import { API_BASE_URL, getHealthSnapshot, type HealthSnapshot } from '@/lib/api';
import { queryKeys } from '@/lib/query-keys';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const LINKS = [
  { href: '/', label: 'Browse', icon: Home },
  { href: '/upload', label: 'Upload', icon: Upload },
  { href: '/jobs', label: 'Jobs', icon: Workflow },
  { href: '/review', label: 'Review', icon: ClipboardCheck },
  { href: '/search', label: 'Search', icon: Search },
  { href: '/catalog', label: 'Catalog', icon: Library },
] as const;

export default function TopNav() {
  const pathname = usePathname() || '/';
  const [open, setOpen] = useState(false);

  const { data: health = { api: 'unknown', ready: 'unknown' } as HealthSnapshot } = useQuery({
    queryKey: queryKeys.health.snapshot,
    queryFn: getHealthSnapshot,
    refetchInterval: 30_000,
  });

  const env = health.env || process.env.NEXT_PUBLIC_APP_ENV || process.env.NODE_ENV || 'dev';

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname === href || pathname.startsWith(`${href}/`);

  return (
    <header className="sticky top-0 z-40 border-b border-cinetag-border/80 bg-cinetag-ink/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-4 px-5 py-3">
        <div className="flex items-center gap-8">
          <Link href="/" className="group flex items-center gap-2.5">
            <span className="relative grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-cinetag-redGlow to-cinetag-redDark shadow-glow ring-1 ring-white/10">
              <Clapperboard className="h-4 w-4 text-white" aria-hidden />
            </span>
            <span className="text-[17px] font-extrabold tracking-tight">
              Cine<span className="text-cinetag-redGlow">Tag</span>
            </span>
            <span className="hidden md:inline-flex chip-neutral text-[10px] uppercase tracking-wider !rounded-full !px-2 !py-0.5">
              video intelligence
            </span>
          </Link>
          <nav className="hidden md:flex items-center gap-1">
            {LINKS.map((l) => {
              const Icon = l.icon;
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className={cn(
                    'inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                    isActive(l.href)
                      ? 'bg-white/8 text-white shadow-inner ring-1 ring-white/10'
                      : 'text-white/65 hover:text-white hover:bg-white/5',
                  )}
                >
                  <Icon className="h-3.5 w-3.5 opacity-70" aria-hidden />
                  {l.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center gap-2">
          <SystemHealthIndicator health={health} />
          <span className="hidden lg:inline-flex chip-neutral !text-[10px] uppercase tracking-wider">
            <span className="text-white/50">env</span>
            <span className="text-white/90">{env}</span>
          </span>
          <Button variant="ghost" size="sm" className="hidden md:inline-flex !text-xs" asChild>
            <a href="/docs" target="_blank" rel="noreferrer noopener">
              API Docs
              <ExternalLink className="h-3 w-3 opacity-60" />
            </a>
          </Button>
          <Button size="sm" className="hidden sm:inline-flex !text-xs" asChild>
            <Link href="/upload">
              <Upload className="h-3.5 w-3.5" />
              Upload
            </Link>
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label="Toggle navigation"
            onClick={() => setOpen((v) => !v)}
            className="md:hidden"
          >
            <Menu className="h-5 w-5" />
          </Button>
        </div>
      </div>

      {open ? (
        <div className="md:hidden border-t border-cinetag-border/70 bg-cinetag-ink animate-in slide-in-from-top-2 duration-200">
          <div className="mx-auto flex max-w-[1400px] flex-col gap-1 px-5 py-3">
            {LINKS.map((l) => {
              const Icon = l.icon;
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className={cn(
                    'inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm',
                    isActive(l.href) ? 'bg-white/10 text-white' : 'text-white/70 hover:bg-white/5 hover:text-white',
                  )}
                >
                  <Icon className="h-4 w-4 opacity-70" />
                  {l.label}
                </Link>
              );
            })}
            <a
              href="/docs"
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm text-white/70 hover:bg-white/5 hover:text-white"
            >
              <ExternalLink className="h-4 w-4 opacity-70" />
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
  const demo = !API_BASE_URL && process.env.NODE_ENV === 'production';
  const label = demo ? 'Demo mode' :
    overall === 'ok' ? 'All systems' : overall === 'down' ? 'API offline' : 'Health unknown';
  return (
    <span title={demo ? "No backend URL configured" : label} className="hidden sm:inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[11px] text-white/70">
      <Activity className="h-3 w-3 opacity-60" aria-hidden />
      <span className={`h-1.5 w-1.5 rounded-full ${demo ? 'bg-amber-400' : dot} animate-pulseSoft`} />
      {label}
    </span>
  );
}
