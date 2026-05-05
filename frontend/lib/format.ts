export function formatBytes(n?: number | null): string {
  if (!n || n <= 0) return '—';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let v = n;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${units[i]}`;
}

export function formatBitsPerSecond(bytesPerSec?: number | null): string {
  if (!bytesPerSec || bytesPerSec <= 0) return '—';
  const bps = bytesPerSec * 8;
  const units = ['bps', 'Kbps', 'Mbps', 'Gbps'];
  let v = bps;
  let i = 0;
  while (v >= 1000 && i < units.length - 1) {
    v /= 1000;
    i++;
  }
  return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${units[i]}`;
}

export function formatDuration(seconds?: number | null): string {
  if (seconds == null || isNaN(seconds) || seconds < 0) return '—';
  const s = Math.floor(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
  return `${m}:${String(sec).padStart(2, '0')}`;
}

export function formatPercent(value?: number | null, digits = 0): string {
  if (value == null || isNaN(value)) return '—';
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatRelativeTime(iso?: string | null): string {
  if (!iso) return '—';
  const t = new Date(iso).getTime();
  if (isNaN(t)) return '—';
  const diffMs = Date.now() - t;
  const diff = Math.abs(diffMs);
  const sec = Math.round(diff / 1000);
  const min = Math.round(sec / 60);
  const hr = Math.round(min / 60);
  const day = Math.round(hr / 24);
  const fmt = (n: number, unit: string) => `${n} ${unit}${n === 1 ? '' : 's'} ${diffMs >= 0 ? 'ago' : 'from now'}`;
  if (sec < 60) return diffMs >= 0 ? 'just now' : 'in a moment';
  if (min < 60) return fmt(min, 'min');
  if (hr < 24) return fmt(hr, 'hour');
  if (day < 30) return fmt(day, 'day');
  return new Date(iso).toLocaleDateString();
}

export function formatNumber(n?: number | null, opts: Intl.NumberFormatOptions = {}): string {
  if (n == null || isNaN(n)) return '—';
  return new Intl.NumberFormat(undefined, opts).format(n);
}

export function clamp(n: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, n));
}

export function truncate(s: string | undefined, n: number): string {
  if (!s) return '';
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}
