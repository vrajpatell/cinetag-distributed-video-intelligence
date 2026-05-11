import type {
  JobSummary,
  Paginated,
  ReviewItem,
  SearchResult,
  VideoPlaybackResponse,
  VideoSummary,
} from './types';

const RAW_API = process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.API_BASE_URL ?? '';
export const API_BASE_URL: string = RAW_API.replace(/\/+$/, '');

const IS_PROD = process.env.NODE_ENV === 'production';
const IS_BROWSER = typeof window !== 'undefined';

let _warnedNoApiBase = false;
function warnNoApiBase(context: string) {
  if (_warnedNoApiBase) return;
  _warnedNoApiBase = true;
  // eslint-disable-next-line no-console
  console.warn(
    `[CineTag] NEXT_PUBLIC_API_BASE_URL is not set${context ? ` (${context})` : ''}.`,
  );
}

if (IS_BROWSER && IS_PROD && !API_BASE_URL) {
  // Spec: "Throw clear error if missing in production."
  // We throw on the client at module load so misconfiguration is loud and
  // fails fast — before any user data is sent over a relative URL that
  // would otherwise hit the frontend's own origin.
  throw new Error(
    '[CineTag] NEXT_PUBLIC_API_BASE_URL is required in production. ' +
      'Pass it as a build arg to the frontend Docker image.',
  );
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
    warnNoApiBase(IS_BROWSER ? 'browser' : 'server');
    return path.startsWith('/') ? path : `/${path}`;
  }
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${p}`;
}

const RAW_API_KEY =
  process.env.NEXT_PUBLIC_API_KEY?.trim() ||
  process.env.NEXT_PUBLIC_REVIEWER_API_KEY?.trim() ||
  process.env.NEXT_PUBLIC_ADMIN_API_KEY?.trim() ||
  '';

function authHeaders(): Record<string, string> {
  if (!RAW_API_KEY) return {};
  return { 'X-API-Key': RAW_API_KEY };
}

export async function apiFetch<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const url = buildUrl(path);
  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(),
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
  // Skip the fetch entirely when no base URL is set on the server: a relative
  // URL has no host in Node, so fetch would always throw and we'd burn time
  // on every SSR request. Surfaces as a single warning per process.
  if (!API_BASE_URL && !IS_BROWSER) {
    warnNoApiBase(`server fallback for ${path}`);
    return fallback;
  }
  try {
    return await apiFetch<T>(path, init);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn(
      `[CineTag] safeFetch fallback for ${path}:`,
      err instanceof Error ? err.message : err,
    );
    return fallback;
  }
}

export interface VideoListParams {
  page?: number;
  page_size?: number;
  status?: string;
  genre?: string;
  mood?: string;
  created_after?: string;
  created_before?: string;
  title_contains?: string;
}

export async function getVideos(params?: VideoListParams): Promise<Paginated<VideoSummary>> {
  const q = new URLSearchParams();
  if (params?.page != null) q.set('page', String(params.page));
  if (params?.page_size != null) q.set('page_size', String(params.page_size));
  if (params?.status) q.set('status', params.status);
  if (params?.genre) q.set('genre', params.genre);
  if (params?.mood) q.set('mood', params.mood);
  if (params?.created_after) q.set('created_after', params.created_after);
  if (params?.created_before) q.set('created_before', params.created_before);
  if (params?.title_contains) q.set('title_contains', params.title_contains);
  const qs = q.toString();
  return apiFetch<Paginated<VideoSummary>>(qs ? `/api/videos?${qs}` : '/api/videos');
}

/** Fetch all pages up to a cap (for dashboards that expect a flat list). */
export async function getVideosFlattened(
  params?: Omit<VideoListParams, 'page' | 'page_size'>,
  maxPages = 25,
): Promise<VideoSummary[]> {
  const out: VideoSummary[] = [];
  let page = 1;
  for (let i = 0; i < maxPages; i += 1) {
    const res = await getVideos({ ...params, page, page_size: 100 });
    out.push(...res.items);
    if (!res.has_next) break;
    page += 1;
  }
  return out;
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

export async function getVideoPlayback(
  id: string | number,
): Promise<VideoPlaybackResponse> {
  return apiFetch<VideoPlaybackResponse>(`/api/videos/${id}/playback`);
}

export interface JobListParams {
  page?: number;
  page_size?: number;
  status?: string;
  current_stage?: string;
  video_id?: number;
  created_after?: string;
  created_before?: string;
}

export async function getJobs(params?: JobListParams): Promise<Paginated<JobSummary>> {
  const q = new URLSearchParams();
  if (params?.page != null) q.set('page', String(params.page));
  if (params?.page_size != null) q.set('page_size', String(params.page_size));
  if (params?.status) q.set('status', params.status);
  if (params?.current_stage) q.set('current_stage', params.current_stage);
  if (params?.video_id != null) q.set('video_id', String(params.video_id));
  if (params?.created_after) q.set('created_after', params.created_after);
  if (params?.created_before) q.set('created_before', params.created_before);
  const qs = q.toString();
  return apiFetch<Paginated<JobSummary>>(qs ? `/api/jobs?${qs}` : '/api/jobs');
}

export async function getJobsFlattened(
  params?: Omit<JobListParams, 'page' | 'page_size'>,
  maxPages = 25,
): Promise<JobSummary[]> {
  const out: JobSummary[] = [];
  let page = 1;
  for (let i = 0; i < maxPages; i += 1) {
    const res = await getJobs({ ...params, page, page_size: 100 });
    out.push(...res.items);
    if (!res.has_next) break;
    page += 1;
  }
  return out;
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

export interface ReviewListParams {
  page?: number;
  page_size?: number;
  status?: string;
  tag_type?: string;
  source?: string;
  video_id?: number;
  created_after?: string;
  created_before?: string;
}

export async function getReviewItems(params?: ReviewListParams): Promise<Paginated<ReviewItem>> {
  const q = new URLSearchParams();
  if (params?.page != null) q.set('page', String(params.page));
  if (params?.page_size != null) q.set('page_size', String(params.page_size));
  if (params?.status) q.set('status', params.status);
  if (params?.tag_type) q.set('tag_type', params.tag_type);
  if (params?.source) q.set('source', params.source);
  if (params?.video_id != null) q.set('video_id', String(params.video_id));
  if (params?.created_after) q.set('created_after', params.created_after);
  if (params?.created_before) q.set('created_before', params.created_before);
  const qs = q.toString();
  return apiFetch<Paginated<ReviewItem>>(qs ? `/api/review?${qs}` : '/api/review');
}

export async function getReviewItemsFlattened(
  params?: Omit<ReviewListParams, 'page' | 'page_size'>,
  maxPages = 25,
): Promise<ReviewItem[]> {
  const out: ReviewItem[] = [];
  let page = 1;
  for (let i = 0; i < maxPages; i += 1) {
    const res = await getReviewItems({ ...params, page, page_size: 100 });
    out.push(...res.items);
    if (!res.has_next) break;
    page += 1;
  }
  return out;
}

export async function patchTag(tagId: number | string, body: { status?: string; tag_value?: string }) {
  return apiFetch(`/api/tags/${tagId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}

export async function publishVideo(id: string | number): Promise<VideoSummary> {
  return apiFetch<VideoSummary>(`/api/videos/${id}/publish`, { method: 'POST' });
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
