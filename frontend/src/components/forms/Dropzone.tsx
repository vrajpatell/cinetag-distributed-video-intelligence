import { useCallback, useId, useRef, useState, type DragEvent } from 'react';
import { UploadCloud, X } from 'lucide-react';
import { cn } from '@/lib/cn';
import { humanizeBytes } from '@/lib/format';

export interface DropzoneProps {
  accept: string[];
  maxSizeBytes?: number;
  file: File | null;
  onChange: (file: File | null) => void;
  disabled?: boolean;
  className?: string;
}

export function Dropzone({
  accept,
  maxSizeBytes,
  file,
  onChange,
  disabled,
  className,
}: DropzoneProps): JSX.Element {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validate = useCallback(
    (candidate: File): string | null => {
      if (accept.length > 0 && !accept.includes(candidate.type) && !accept.some((a) => candidate.name.toLowerCase().endsWith(a))) {
        return `Unsupported file type: ${candidate.type || 'unknown'}`;
      }
      if (maxSizeBytes != null && candidate.size > maxSizeBytes) {
        return `File too large (${humanizeBytes(candidate.size)} > ${humanizeBytes(maxSizeBytes)})`;
      }
      return null;
    },
    [accept, maxSizeBytes],
  );

  const handleFile = useCallback(
    (next: File | null) => {
      if (!next) {
        setError(null);
        onChange(null);
        return;
      }
      const e = validate(next);
      if (e) {
        setError(e);
        onChange(null);
        return;
      }
      setError(null);
      onChange(next);
    },
    [onChange, validate],
  );

  const onDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setDragOver(false);
    if (disabled) return;
    const dropped = e.dataTransfer.files?.[0] ?? null;
    handleFile(dropped);
  };

  const onDragOver = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    if (!disabled) setDragOver(true);
  };

  const onDragLeave = () => setDragOver(false);

  return (
    <div className={cn('w-full', className)}>
      <label
        htmlFor={inputId}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        className={cn(
          'group relative flex min-h-[200px] cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-bg-3 bg-bg-1 p-8 text-center transition-all',
          'hover:border-accent/60 hover:bg-bg-2',
          'focus-within:outline-none focus-within:ring-2 focus-within:ring-accent focus-within:ring-offset-2 focus-within:ring-offset-bg-0',
          dragOver && 'border-accent bg-accent/10 shadow-[0_0_0_3px_rgba(229,9,20,0.25)]',
          disabled && 'pointer-events-none opacity-60',
        )}
      >
        <input
          id={inputId}
          ref={inputRef}
          type="file"
          accept={accept.join(',')}
          className="sr-only"
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
          disabled={disabled}
        />
        <UploadCloud className={cn('h-10 w-10 text-text-2 transition-colors group-hover:text-accent', dragOver && 'text-accent')} aria-hidden />
        <div>
          <p className="text-sm font-semibold text-text-0">Drop a video here, or click to browse</p>
          <p className="mt-1 text-xs text-text-2">
            Accepted: {accept.join(', ')}
            {maxSizeBytes ? ` · Max ${humanizeBytes(maxSizeBytes)}` : ''}
          </p>
        </div>
      </label>

      {file && (
        <div className="mt-3 flex items-center justify-between gap-4 rounded-md border border-bg-3 bg-bg-1 px-4 py-3">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-text-0">{file.name}</p>
            <p className="text-xs text-text-2">
              {humanizeBytes(file.size)} · {file.type || 'application/octet-stream'}
            </p>
          </div>
          <button
            type="button"
            aria-label="Remove file"
            onClick={() => {
              if (inputRef.current) inputRef.current.value = '';
              handleFile(null);
            }}
            className="rounded-md p-1.5 text-text-1 transition-colors hover:bg-bg-2 hover:text-text-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
      )}

      {error && (
        <p role="alert" className="mt-2 text-sm text-accent">
          {error}
        </p>
      )}
    </div>
  );
}
