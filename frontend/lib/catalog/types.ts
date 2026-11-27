export type Cell = string | number | null;
export type FieldKind =
  | 'text'
  | 'integer'
  | 'decimal'
  | 'datetime'
  | 'seconds'
  | 'milliseconds'
  | 'bytes'
  | 'confidence';
export type Operator =
  | 'eq'
  | 'ne'
  | 'contains'
  | 'starts_with'
  | 'gte'
  | 'lte'
  | 'missing'
  | 'present';
export type ExportFormat = 'csv' | 'json' | 'ndjson';
export type DeliveryFormat =
  | 'manifest'
  | 'transcript'
  | 'chapters'
  | 'ffmetadata'
  | 'tags'
  | 'cue-sheet'
  | 'bundle';

export interface Column {
  id: string;
  label: string;
  kind: FieldKind;
  operators: Operator[];
  groupable: boolean;
  measurable: boolean;
}
export interface Preset {
  id: string;
  label: string;
  description: string;
}
export interface Sort {
  field: string;
  direction: 'asc' | 'desc';
}
export interface Dataset {
  id: string;
  label: string;
  description: string;
  fields: Column[];
  default_columns: string[];
  default_sort: Sort;
  presets: Preset[];
}
export interface Schema {
  datasets: Dataset[];
  export_limit: number;
}
export interface Filter {
  field: string;
  operator: Operator;
  value?: string;
}
export interface Selection {
  search: string;
  filters: Filter[];
  preset: string | null;
}
export interface View extends Selection {
  columns: string[];
  sort: Sort;
  page_size: number;
}
export interface RecordRow {
  id: number;
  video_id: number | null;
  cells: Record<string, Cell>;
}
export interface Results {
  dataset: string;
  columns: string[];
  rows: RecordRow[];
  total: number;
  page: number;
  page_size: number;
}
export interface Breakdown {
  field: string;
  groups: { value: Cell; count: number }[];
  total: number;
  remaining: number;
}
export interface QualityCheck {
  dataset: string;
  dataset_label: string;
  preset: string;
  label: string;
  description: string;
  count: number;
}
export interface Quality {
  checked_at: string;
  checks: QualityCheck[];
}
export interface DeliveryPreview {
  video_id: number;
  title: string;
  approved_tags: number;
  chapters: number;
  transcript_available: boolean;
  files: {
    format: DeliveryFormat;
    filename: string;
    available: boolean;
    reason: string | null;
  }[];
  notices: { code: string; scene_id: number | null; message: string }[];
}

export const operators: Record<Operator, string> = {
  eq: 'Equals',
  ne: 'Does not equal',
  contains: 'Contains',
  starts_with: 'Starts with',
  gte: 'At least',
  lte: 'At most',
  missing: 'Is missing',
  present: 'Is present',
};

export function needsValue(op: Operator) {
  return op !== 'missing' && op !== 'present';
}

export function initialView(dataset: Dataset, preset: string | null = null): View {
  return {
    preset,
    filters: [],
    search: '',
    columns: [...dataset.default_columns],
    sort: { ...dataset.default_sort },
    page_size: 25,
  };
}

export interface Distribution {
  field: string;
  total: number;
  measured: number;
  missing: number;
  minimum: number | null;
  maximum: number | null;
  mean: number | null;
  median: number | null;
  p90: number | null;
  p95: number | null;
}
