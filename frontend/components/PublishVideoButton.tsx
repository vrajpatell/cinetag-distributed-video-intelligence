'use client';

import { useState } from 'react';
import { ApiError, publishVideo } from '@/lib/api';

export default function PublishVideoButton({
  videoId,
  initialStatus,
}: {
  videoId: number | string;
  initialStatus?: string;
}) {
  const [status, setStatus] = useState<string | undefined>(initialStatus);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (status === 'published') {
    return (
      <span className="chip-neutral !text-[10.5px] uppercase tracking-wider text-emerald-300">
        published
      </span>
    );
  }

  const canPublish = status === 'review_ready';

  return (
    <div className="space-y-2">
      <button
        type="button"
        disabled={!canPublish || busy}
        onClick={async () => {
          setBusy(true);
          setError(null);
          try {
            const updated = await publishVideo(videoId);
            setStatus(String(updated.status || 'published'));
          } catch (err) {
            const msg =
              err instanceof ApiError
                ? err.detail || err.message
                : err instanceof Error
                ? err.message
                : 'Publish failed';
            setError(msg);
          } finally {
            setBusy(false);
          }
        }}
        className={[
          'btn !text-xs',
          canPublish
            ? 'bg-emerald-500/90 text-black hover:bg-emerald-400'
            : 'bg-white/5 text-white/45 ring-1 ring-white/10 cursor-not-allowed',
        ].join(' ')}
      >
        {busy ? 'Publishing…' : 'Publish video'}
      </button>
      {!canPublish && status !== 'published' ? (
        <p className="text-[11px] text-white/55">
          Resolve all pending tag reviews before publishing.
        </p>
      ) : null}
      {error ? <p className="text-[11px] text-rose-300">{error}</p> : null}
    </div>
  );
}
