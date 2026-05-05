'use client';

export interface ErrorDetail {
  title?: string;
  message?: string;
  endpoint?: string;
  status?: number;
  hint?: string;
}

export default function ErrorToast({
  error,
  onDismiss,
  onRetry,
}: {
  error: ErrorDetail | null;
  onDismiss?: () => void;
  onRetry?: () => void;
}) {
  if (!error) return null;
  return (
    <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-rose-50">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 grid h-7 w-7 place-items-center rounded-full bg-rose-500/30 ring-1 ring-rose-500/50">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
            <path d="M12 9v4m0 4h.01M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.7 3.86a2 2 0 0 0-3.4 0Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold">{error.title || 'Something went wrong'}</div>
          {error.message ? <p className="mt-0.5 text-[12.5px] text-rose-100/90">{error.message}</p> : null}
          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[11px] text-rose-100/75">
            {error.status != null ? <span>status {error.status}</span> : null}
            {error.endpoint ? <span className="truncate">{error.endpoint}</span> : null}
          </div>
          {error.hint ? <p className="mt-1 text-[12px] text-rose-100/80">{error.hint}</p> : null}
          {(onDismiss || onRetry) && (
            <div className="mt-2 flex gap-2">
              {onRetry ? (
                <button
                  type="button"
                  onClick={onRetry}
                  className="btn !px-2.5 !py-1 !text-xs bg-white text-rose-600 hover:bg-rose-100"
                >
                  Retry
                </button>
              ) : null}
              {onDismiss ? (
                <button
                  type="button"
                  onClick={onDismiss}
                  className="btn-ghost !px-2.5 !py-1 !text-xs text-rose-50/85 hover:text-white"
                >
                  Dismiss
                </button>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
