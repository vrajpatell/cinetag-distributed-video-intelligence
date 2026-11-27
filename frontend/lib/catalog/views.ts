import { needsValue, type Dataset, type Filter, type View } from './types';

const STORAGE_KEY = 'cinetag.catalog.views.v1';
export const MAX_VIEWS = 30;

export interface SavedView {
  name: string;
  dataset: string;
  view: View;
}

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function validFilter(value: unknown, dataset: Dataset): value is Filter {
  if (!object(value)) return false;
  const field = dataset.fields.find((col) => col.id === value.field);
  const operator = field?.operators.find((op) => op === value.operator);
  if (!operator) return false;
  if (!needsValue(operator)) return value.value == null;
  return typeof value.value === 'string' && !!value.value.trim() && value.value.length <= 512;
}

export function validateView(raw: unknown, dataset: Dataset): raw is View {
  if (!object(raw) || typeof raw.search !== 'string' || raw.search.length > 256) return false;
  if (raw.preset !== null && !dataset.presets.some((item) => item.id === raw.preset)) return false;
  if (
    !Array.isArray(raw.filters) ||
    raw.filters.length > 12 ||
    !raw.filters.every((item) => validFilter(item, dataset))
  )
    return false;
  const fields = new Set(dataset.fields.map((field) => field.id));
  if (
    !Array.isArray(raw.columns) ||
    !raw.columns.length ||
    !raw.columns.every((key) => fields.has(key))
  )
    return false;
  if (new Set(raw.columns).size !== raw.columns.length) return false;
  const sort = raw.sort;
  if (!object(sort) || typeof sort.field !== 'string' || !fields.has(sort.field)) return false;
  if (sort.direction !== 'asc' && sort.direction !== 'desc') return false;
  return (
    raw.page_size === 10 || raw.page_size === 25 || raw.page_size === 50 || raw.page_size === 100
  );
}

export function readSavedViews(datasets: Dataset[]): SavedView[] {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (!stored) return [];
  let raw: unknown;
  try {
    raw = JSON.parse(stored);
  } catch {
    return [];
  }
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((item): item is SavedView => {
      if (
        !object(item) ||
        typeof item.name !== 'string' ||
        !item.name.trim() ||
        item.name.length > 64
      )
        return false;
      const dataset = datasets.find((candidate) => candidate.id === item.dataset);
      return !!dataset && validateView(item.view, dataset);
    })
    .slice(0, MAX_VIEWS);
}

export function saveView(datasets: Dataset[], entry: SavedView) {
  const saved = readSavedViews(datasets);
  const name = entry.name.trim();
  if (!name || name.length > 64) throw new Error('Use a view name between 1 and 64 characters.');
  if (saved.some((item) => item.dataset === entry.dataset && item.name === name)) {
    throw new Error('A view with that name already exists for this dataset.');
  }
  if (saved.length >= MAX_VIEWS)
    throw new Error(`Remove a saved view before adding another (limit ${MAX_VIEWS}).`);
  const next = [...saved, { ...entry, name }];
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  return next;
}

export function removeView(datasets: Dataset[], entry: SavedView) {
  const saved = readSavedViews(datasets);
  const next = saved.filter((item) => item.dataset !== entry.dataset || item.name !== entry.name);
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  return next;
}
