import Link from 'next/link';

export default function EmptyState({
  title,
  description,
  hint,
  action,
}: {
  title: string;
  description?: string;
  hint?: string;
  action?: { label: string; href: string };
}) {
  return (
    <div className="panel relative overflow-hidden p-8 text-center">
      <div className="pointer-events-none absolute inset-0 grid-bg opacity-30" />
      <div className="relative mx-auto max-w-md">
        <div className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-cinetag-red/15 text-cinetag-redGlow ring-1 ring-cinetag-red/30">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
            <rect x="4" y="6" width="16" height="12" rx="2" stroke="currentColor" strokeWidth="2" />
            <path d="m9 10 6 4-6 4z" fill="currentColor" />
          </svg>
        </div>
        <h3 className="mt-4 text-lg font-semibold text-white">{title}</h3>
        {description ? <p className="mt-1 text-sm text-white/60">{description}</p> : null}
        {hint ? <p className="mt-2 text-[11.5px] text-white/40">{hint}</p> : null}
        {action ? (
          <div className="mt-5">
            <Link href={action.href} className="btn-primary !px-4">
              {action.label}
            </Link>
          </div>
        ) : null}
      </div>
    </div>
  );
}
