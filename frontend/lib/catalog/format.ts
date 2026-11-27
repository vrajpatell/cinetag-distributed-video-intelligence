import { formatDuration, formatPercent } from '@/lib/format';
import type { Cell, FieldKind } from './types';

export function displayCell(value: Cell, kind?: FieldKind) {
  if (value === null || value === '') return '—';
  if (typeof value === 'number') {
    if (kind === 'seconds') return formatDuration(value);
    if (kind === 'confidence') return formatPercent(value, 1);
    if (kind === 'milliseconds') return `${value.toLocaleString()} ms`;
    if (kind === 'bytes') {
      if (value < 1024) return `${value.toLocaleString()} B`;
      if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KiB`;
      if (value < 1024 ** 3) return `${(value / 1024 ** 2).toFixed(1)} MiB`;
      return `${(value / 1024 ** 3).toFixed(1)} GiB`;
    }
    return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
  }
  if (kind === 'datetime') {
    const date = new Date(value);
    if (Number.isFinite(date.valueOf())) return date.toLocaleString();
  }
  return String(value);
}

export const inputClass =
  'rounded-md border border-white/20 bg-zinc-950 px-3 py-2 text-sm text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-white/70';
