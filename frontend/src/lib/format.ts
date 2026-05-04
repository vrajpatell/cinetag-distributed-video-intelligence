export function humanizeBytes(bytes: number | null | undefined): string {
  if (bytes == null || Number.isNaN(bytes) || bytes < 0) return '—';
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const idx = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
  const value = bytes / Math.pow(1024, idx);
  const decimals = idx === 0 ? 0 : value >= 100 ? 0 : value >= 10 ? 1 : 2;
  return `${value.toFixed(decimals)} ${units[idx]}`;
}

export function humanizeDuration(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds) || seconds < 0) return '—';
  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}h ${m.toString().padStart(2, '0')}m`;
  if (m > 0) return `${m}m ${s.toString().padStart(2, '0')}s`;
  return `${s}s`;
}

export function humanizeMs(ms: number | null | undefined): string {
  if (ms == null || Number.isNaN(ms) || ms < 0) return '—';
  if (ms < 1000) return `${ms} ms`;
  return humanizeDuration(ms / 1000);
}

const RTF = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });

export function formatRelative(input: string | Date | null | undefined): string {
  if (!input) return '—';
  const d = typeof input === 'string' ? new Date(input) : input;
  if (Number.isNaN(d.getTime())) return '—';
  const diffSeconds = (d.getTime() - Date.now()) / 1000;
  const abs = Math.abs(diffSeconds);
  const intervals: Array<[number, Intl.RelativeTimeFormatUnit]> = [
    [60, 'second'],
    [3600, 'minute'],
    [86400, 'hour'],
    [604800, 'day'],
    [2629800, 'week'],
    [31557600, 'month'],
    [Number.POSITIVE_INFINITY, 'year'],
  ];
  let unitDivisor = 1;
  let unit: Intl.RelativeTimeFormatUnit = 'second';
  for (let i = 0; i < intervals.length; i += 1) {
    const [threshold, candidate] = intervals[i];
    if (abs < threshold) {
      unit = candidate;
      unitDivisor = i === 0 ? 1 : intervals[i - 1][0];
      break;
    }
  }
  return RTF.format(Math.round(diffSeconds / unitDivisor), unit);
}

export function formatResolution(w: number | null | undefined, h: number | null | undefined): string {
  if (w == null || h == null) return '—';
  return `${w}×${h}`;
}

export function formatPercent(n: number | null | undefined, fractionDigits = 0): string {
  if (n == null || Number.isNaN(n)) return '—';
  return `${(n * 100).toFixed(fractionDigits)}%`;
}

export function truncate(text: string | null | undefined, max: number): string {
  if (!text) return '';
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1).trimEnd()}…`;
}

export function initialsOf(name: string | null | undefined, fallback = 'CT'): string {
  if (!name) return fallback;
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() ?? '').join('') || fallback;
}
