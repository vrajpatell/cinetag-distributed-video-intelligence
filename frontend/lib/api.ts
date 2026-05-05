import type {
  JobSummary,
  ReviewItem,
  SearchResult,
  VideoSummary,
} from './types';

const RAW_API = process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.API_BASE_URL ?? '';
export const API_BASE_URL: string = RAW_API.replace(/\/+$/, '');

if (
  typeof window !== 'undefined' &&
  process.env.NODE_ENV === 'production' &&
  !API_BASE_URL
) {
  console.warn('[CineTag] NEXT_PUBLIC_API_BASE_URL is not set in production.');
}

export class ApiError extends Error {
  status?: number;
  endpoint: string;
  detail?: string;
  constructor(message: string, opts: { status?: number; endpoint: string; detail?: string }) {
    super(message);
    this.name = 'ApiError';
    this.status = opts.status;
    this.endpoint = opts.endpoint;
    this.detail = opts.detail;
  }
}

function buildUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  if (!API_BASE_URL) {
    return path.startsWith('/') ? path : `/${path}`;
  }
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${p}`;
}

export async function apiFetch<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const url = buildUrl(path);
  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers || {}),
      },
      cache: init?.cache ?? 'no-store',
    });
  } catch (err) {
    const message =
      err instanceof Error
        ? err.message || 'Network request failed'
        : 'Network request failed';
    throw new ApiError(message, { endpoint: url });
  }
  let body: unknown;
  const text = await res.text();
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!res.ok) {
    const detail =
      (body as { detail?: string } | null)?.detail ||
      (typeof body === 'string' ? body : '') ||
      res.statusText;
    throw new ApiError(`Request failed (${res.status}) ${detail || ''}`.trim(), {
      status: res.status,
      endpoint: url,
      detail,
    });
  }
  return body as T;
}

export async function safeFetch<T>(path: string, fallback: T, init?: RequestInit): Promise<T> {
  try {
    return await apiFetch<T>(path, init);
  } catch {
    return fallback;
  }
}

export async function getVideos(): Promise<VideoSummary[]> {
  return apiFetch<VideoSummary[]>('/api/videos');
}

export async function getVideo(id: string | number): Promise<VideoSummary> {
  return apiFetch<VideoSummary>(`/api/videos/${id}`);
}

export async function getVideoTags(id: string | number) {
  return apiFetch<unknown[]>(`/api/videos/${id}/tags`);
}

export async function getVideoTranscript(id: string | number) {
  return apiFetch<unknown>(`/api/videos/${id}/transcript`);
}

export async function getJobs(): Promise<JobSummary[]> {
  return apiFetch<JobSummary[]>('/api/jobs');
}

export async function getJob(id: string | number): Promise<JobSummary> {
  return apiFetch<JobSummary>(`/api/jobs/${id}`);
}

export async function retryJob(id: string | number): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/api/jobs/${id}/retry`, { method: 'POST' });
}

export interface UploadInitInput {
  filename: string;
  content_type: string;
  size_bytes: number;
  title?: string;
}
export interface UploadInitResponse {
  video_id: number;
  storage_key: string;
  upload_url: string;
  upload_method: string;
  required_headers: Record<string, string>;
  expires_in_seconds: number;
}
export async function initUpload(input: UploadInitInput): Promise<UploadInitResponse> {
  return apiFetch<UploadInitResponse>('/api/uploads/init', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export interface UploadCompleteInput {
  video_id: number;
  storage_key: string;
  title?: string;
}
export interface UploadCompleteResponse {
  video_id: number;
  job_id: number;
  status: string;
}
export async function completeUpload(input: UploadCompleteInput): Promise<UploadCompleteResponse> {
  return apiFetch<UploadCompleteResponse>('/api/uploads/complete', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export interface SearchInput {
  query: string;
  tag_type?: string;
  status?: string;
  duration_min?: number;
  duration_max?: number;
}
export async function searchVideos(input: SearchInput): Promise<SearchResult[]> {
  return apiFetch<SearchResult[]>('/api/search/semantic', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function getReviewItems(): Promise<ReviewItem[]> {
  // No explicit /api/review endpoint exists in backend; we synthesize one by
  // pulling tags-with-pending-review across videos. If that endpoint isn't
  // available, callers should fall back to demo data.
  try {
    return await apiFetch<ReviewItem[]>('/api/review');
  } catch {
    return [];
  }
}

export async function patchTag(tagId: number | string, body: { status?: string; tag_value?: string }) {
  return apiFetch(`/api/tags/${tagId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}

export interface HealthSnapshot {
  api: 'ok' | 'down' | 'unknown';
  ready: 'ok' | 'down' | 'unknown';
  env?: string;
}
export async function getHealthSnapshot(): Promise<HealthSnapshot> {
  const out: HealthSnapshot = { api: 'unknown', ready: 'unknown' };
  try {
    const h = await apiFetch<{ status: string; env?: string }>('/health');
    out.api = h?.status === 'ok' ? 'ok' : 'unknown';
    out.env = h?.env;
  } catch {
    out.api = 'down';
  }
  try {
    const r = await apiFetch<{ status: string }>('/ready');
    out.ready = r?.status === 'ready' ? 'ok' : 'unknown';
  } catch {
    out.ready = 'down';
  }
  return out;
}
