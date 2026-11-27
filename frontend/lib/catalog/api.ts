import type { Distribution } from './types';
import { apiFetch, apiFetchBlob } from '@/lib/api';
import type {
  Breakdown,
  DeliveryFormat,
  DeliveryPreview,
  ExportFormat,
  Quality,
  Results,
  Schema,
  Selection,
  View,
} from './types';

function post(body: unknown, signal?: AbortSignal): RequestInit {
  return { method: 'POST', body: JSON.stringify(body), signal };
}

function reportPath(dataset: string, action: string) {
  return `/api/catalog/${encodeURIComponent(dataset)}/${action}`;
}

export function catalogSchema(signal?: AbortSignal) {
  return apiFetch<Schema>('/api/catalog/schema', { signal });
}

export function catalogQuality(signal?: AbortSignal) {
  return apiFetch<Quality>('/api/catalog/quality', { signal });
}

export function catalogRows(dataset: string, view: View, page: number, signal?: AbortSignal) {
  return apiFetch<Results>(reportPath(dataset, 'query'), post({ ...view, page }, signal));
}

export function catalogBreakdown(
  dataset: string,
  selection: Selection,
  field: string,
  signal?: AbortSignal,
) {
  return apiFetch<Breakdown>(reportPath(dataset, 'groups'), post({ ...selection, field }, signal));
}

export function exportReport(dataset: string, view: View, format: ExportFormat) {
  return apiFetchBlob(reportPath(dataset, 'export'), post({ ...view, format }));
}

export function deliveryPreview(id: string | number, signal?: AbortSignal) {
  return apiFetch<DeliveryPreview>(`/api/videos/${encodeURIComponent(id)}/delivery`, { signal });
}

export function deliveryFile(id: string | number, format: DeliveryFormat) {
  return apiFetchBlob(`/api/videos/${encodeURIComponent(id)}/delivery/files/${format}`);
}

export function saveDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function catalogDistribution(
  dataset: string,
  selection: Selection,
  field: string,
  signal?: AbortSignal,
) {
  return apiFetch<Distribution>(
    reportPath(dataset, 'distribution'),
    post({ ...selection, field }, signal),
  );
}
