'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { deliveryFile, deliveryPreview, saveDownload } from '@/lib/catalog/api';
import type { DeliveryFormat } from '@/lib/catalog/types';

const labels: Record<DeliveryFormat, string> = {
  bundle: 'Download delivery ZIP',
  manifest: 'Metadata manifest · JSON',
  transcript: 'Transcript · TXT',
  chapters: 'Chapter track · WebVTT',
  ffmetadata: 'FFmpeg chapter metadata',
  tags: 'Approved tags · CSV',
  'cue-sheet': 'Scene cue sheet · CSV',
};

export default function DeliveryPanel({ videoId }: { videoId: number | string }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<DeliveryFormat | null>(null);
  const [error, setError] = useState('');
  const query = useQuery({
    queryKey: ['delivery-preview', videoId],
    queryFn: ({ signal }) => deliveryPreview(videoId, signal),
    enabled: open,
  });
  async function download(format: DeliveryFormat, name: string) {
    setBusy(format);
    setError('');
    try {
      const blob = await deliveryFile(videoId, format);
      saveDownload(blob, `cinetag-${videoId}-${name}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download failed.');
    } finally {
      setBusy(null);
    }
  }
  return (
    <details className="panel p-4" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary className="cursor-pointer font-semibold">Export video metadata</summary>
      {open && (
        <div className="mt-3 space-y-3">
          {query.isPending && <p role="status">Preparing file list…</p>}
          {query.isError && (
            <p role="alert">
              {query.error.message}{' '}
              <button onClick={() => query.refetch()} className="underline">
                Retry
              </button>
            </p>
          )}
          {query.data && (
            <>
              <p className="text-sm text-white/60">
                {query.data.chapters} chapters · {query.data.approved_tags} approved tags
              </p>
              <ul className="space-y-2">
                {[...query.data.files]
                  .sort((a, b) => Number(b.format === 'bundle') - Number(a.format === 'bundle'))
                  .map((file) => (
                    <li key={file.format}>
                      <button
                        type="button"
                        disabled={!file.available || !!busy}
                        onClick={() => download(file.format, file.filename)}
                        className={
                          file.format === 'bundle'
                            ? 'btn-primary'
                            : 'text-left text-sm underline disabled:text-white/40'
                        }
                      >
                        {busy === file.format ? 'Downloading…' : labels[file.format]}
                      </button>
                      {file.reason && <p className="text-xs text-white/55">{file.reason}</p>}
                    </li>
                  ))}
              </ul>
              {query.data.notices.length > 0 && (
                <details className="text-xs text-amber-200">
                  <summary className="cursor-pointer">
                    Scene adjustments ({query.data.notices.length})
                  </summary>
                  <ul className="mt-2 space-y-1">
                    {query.data.notices.map((notice, index) => (
                      <li key={index}>
                        Scene {notice.scene_id} · {notice.message}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </>
          )}
          {error && (
            <p role="alert" className="text-sm text-rose-300">
              {error}
            </p>
          )}
        </div>
      )}
    </details>
  );
}
