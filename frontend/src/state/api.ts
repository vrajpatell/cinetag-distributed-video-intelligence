import axios, { AxiosError, type AxiosInstance } from 'axios';
import { toast } from '@/components/ui/toastStore';

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ||
  'http://localhost:8000';

export const apiOrigin: string = (() => {
  try {
    return new URL(API_BASE_URL).origin;
  } catch {
    return API_BASE_URL;
  }
})();

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  headers: { Accept: 'application/json' },
});

function extractErrorMessage(error: AxiosError): string {
  const data = error.response?.data as unknown;
  if (data && typeof data === 'object') {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d) => {
          if (d && typeof d === 'object' && 'msg' in d) return String((d as { msg: unknown }).msg);
          return JSON.stringify(d);
        })
        .join(', ');
    }
    if (typeof (data as { message?: unknown }).message === 'string') {
      return (data as { message: string }).message;
    }
  }
  return error.message || 'Unexpected error';
}

api.interceptors.response.use(
  (resp) => resp,
  (error: AxiosError) => {
    if (axios.isCancel(error) || error.code === 'ERR_CANCELED') {
      return Promise.reject(error);
    }
    const status = error.response?.status;
    const message = extractErrorMessage(error);
    const url = error.config?.url ?? '';
    const isMutation =
      error.config?.method && ['post', 'put', 'patch', 'delete'].includes(error.config.method.toLowerCase());
    if (isMutation || (status && status >= 500)) {
      toast.danger(
        status ? `Request failed (${status})` : 'Network error',
        `${message}${url ? ` · ${url}` : ''}`,
      );
    }
    return Promise.reject(error);
  },
);
