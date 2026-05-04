import { useSyncExternalStore } from 'react';

export type ToastTone = 'info' | 'success' | 'warning' | 'danger';

export interface Toast {
  id: string;
  title: string;
  description?: string;
  tone: ToastTone;
  durationMs: number;
}

type Listener = () => void;

interface ToastInput {
  title: string;
  description?: string;
  tone?: ToastTone;
  durationMs?: number;
}

const listeners = new Set<Listener>();
let toasts: Toast[] = [];

function emit() {
  for (const l of listeners) l();
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function pushToast(input: ToastInput): string {
  const t: Toast = {
    id: generateId(),
    title: input.title,
    description: input.description,
    tone: input.tone ?? 'info',
    durationMs: input.durationMs ?? 4500,
  };
  toasts = [...toasts, t];
  emit();
  if (t.durationMs > 0) {
    setTimeout(() => dismissToast(t.id), t.durationMs);
  }
  return t.id;
}

export function dismissToast(id: string): void {
  const before = toasts.length;
  toasts = toasts.filter((t) => t.id !== id);
  if (toasts.length !== before) emit();
}

function subscribe(l: Listener): () => void {
  listeners.add(l);
  return () => {
    listeners.delete(l);
  };
}

function getSnapshot(): Toast[] {
  return toasts;
}

export function useToasts(): Toast[] {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

export const toast = {
  info: (title: string, description?: string) => pushToast({ title, description, tone: 'info' }),
  success: (title: string, description?: string) => pushToast({ title, description, tone: 'success' }),
  warning: (title: string, description?: string) => pushToast({ title, description, tone: 'warning' }),
  danger: (title: string, description?: string) => pushToast({ title, description, tone: 'danger' }),
};
