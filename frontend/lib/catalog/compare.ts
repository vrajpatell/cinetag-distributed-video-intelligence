import { apiFetch } from '@/lib/api';
import type { Cell, FieldKind } from './types';

export interface AssetRef {
  id: number;
  title: string;
}
export interface Metric {
  id: string;
  group: string;
  label: string;
  kind: FieldKind;
  left: Cell;
  right: Cell;
  relation: 'equal' | 'different' | 'left_only' | 'right_only' | 'unknown';
}
export interface LabelMatch {
  type: string;
  value: string;
}
export interface Comparison {
  left: AssetRef;
  right: AssetRef;
  metrics: Metric[];
  tags: {
    shared: LabelMatch[];
    left_only: LabelMatch[];
    right_only: LabelMatch[];
    similarity: number | null;
  };
  speech: {
    unique_left: number;
    unique_right: number;
    shared_words: number;
    vocabulary_similarity: number | null;
    frequent_shared: {
      word: string;
      left_count: number;
      right_count: number;
    }[];
  };
}

export function compareVideos(left: number, right: number, signal?: AbortSignal) {
  const query = new URLSearchParams({ left: String(left), right: String(right) });
  return apiFetch<Comparison>(`/api/catalog/compare?${query}`, { signal });
}
