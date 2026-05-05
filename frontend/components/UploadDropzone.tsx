'use client';

import { useCallback, useRef, useState } from 'react';
import { formatBytes } from '@/lib/format';

const ACCEPT = 'video/mp4,video/quicktime,video/x-matroska,.mp4,.mov,.mkv';
const ACCEPTED_EXTS = ['.mp4', '.mov', '.mkv'];

export default function UploadDropzone({
  file,
  onFile,
  maxSizeMb = 5_000,
  disabled = false,
}: {
  file: File | null;
  onFile: (f: File | null) => void;
  maxSizeMb?: number;
  disabled?: boolean;
}) {
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = useCallback(
    (f: File): string | null => {
      const lower = f.name.toLowerCase();
      const okExt = ACCEPTED_EXTS.some((e) => lower.endsWith(e));
      const okMime = /^video\/(mp4|quicktime|x-matroska)$/i.test(f.type);
      if (!okExt && !okMime) return 'Unsupported file type. Use .mp4, .mov, or .mkv.';
      if (f.size > maxSizeMb * 1024 * 1024) {
        return `File is too large (${formatBytes(f.size)}). Max ${maxSizeMb} MB.`;
      }
      return null;
    },
    [maxSizeMb]
  );

  const handle = (f: File | null) => {
    if (!f) {
      onFile(null);
      setError(null);
      return;
    }
    const err = validate(f);
    if (err) {
      setError(err);
      onFile(null);
      return;
    }
    setError(null);
    onFile(f);
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          if (disabled) return;
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          if (disabled) return;
          e.preventDefault();
          setDrag(false);
          const f = e.dataTransfer.files?.[0] || null;
          handle(f);
        }}
        className={[
          'relative grid place-items-center rounded-2xl border-2 border-dashed px-6 py-12 transition-all',
          drag
            ? 'border-cinetag-red/70 bg-cinetag-red/5'
            : 'border-cinetag-border bg-cinetag-panel/50 hover:border-white/25',
          disabled ? 'opacity-60 pointer-events-none' : '',
        ].join(' ')}
      >
        <div className="pointer-events-none absolute inset-x-6 top-6 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
        <div className="relative flex max-w-md flex-col items-center text-center">
          <div className="grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-cinetag-redGlow/30 to-cinetag-red/10 ring-1 ring-cinetag-red/30 shadow-glow">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path d="M12 16V4m0 0-4 4m4-4 4 4M4 20h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="mt-4 text-base font-semibold text-white">
            Drop a video here, or{' '}
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="text-cinetag-redGlow underline-offset-4 hover:underline"
              disabled={disabled}
            >
              browse files
            </button>
          </div>
          <p className="mt-1 text-[12px] text-white/55">
            Accepted: <span className="font-mono text-white/75">.mp4 .mov .mkv</span>
            <span className="mx-2 text-white/30">•</span>
            Max <span className="font-mono text-white/75">{maxSizeMb} MB</span>
            <span className="mx-2 text-white/30">•</span>
            Direct-to-GCS signed PUT
          </p>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            className="hidden"
            onChange={(e) => handle(e.target.files?.[0] || null)}
          />
        </div>
      </div>

      {error ? (
        <div className="rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-[12.5px] text-rose-200">
          {error}
        </div>
      ) : null}

      {file ? (
        <div className="panel flex flex-wrap items-center gap-4 px-4 py-3">
          <div className="grid h-10 w-10 place-items-center rounded-md bg-cinetag-red/15 text-cinetag-redGlow ring-1 ring-cinetag-red/30">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
              <rect x="3" y="5" width="14" height="14" rx="2" stroke="currentColor" strokeWidth="2" />
              <path d="M17 9l4-2v10l-4-2" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium text-white">{file.name}</div>
            <div className="text-[11px] text-white/55">
              {file.type || 'video/*'} · {formatBytes(file.size)}
            </div>
          </div>
          {!disabled ? (
            <button type="button" className="btn-ghost !px-2.5 !py-1 !text-xs" onClick={() => handle(null)}>
              Clear
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
