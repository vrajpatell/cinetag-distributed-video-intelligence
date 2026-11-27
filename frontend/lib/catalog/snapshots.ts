import { z } from 'zod';
import type { Quality, QualityCheck } from './types';

const checkSchema = z.object({
  dataset: z.string().min(1).max(64),
  dataset_label: z.string().min(1).max(256),
  preset: z.string().min(1).max(64),
  label: z.string().min(1).max(256),
  description: z.string().max(2048),
  count: z.number().int().nonnegative().safe(),
});

const schema = z.object({
  checked_at: z.string().datetime({ offset: true }),
  checks: z.array(checkSchema).max(2048),
});

export type Trend = 'increased' | 'improved' | 'unchanged' | 'added' | 'removed';
export interface Change {
  key: string;
  label: string;
  dataset: string;
  current: QualityCheck | null;
  before: number | null;
  after: number | null;
  delta: number | null;
  trend: Trend;
}

function key(check: QualityCheck) {
  return JSON.stringify([check.dataset, check.preset]);
}

export function parseSnapshot(text: string): Quality {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error('This file contains invalid JSON.');
  }
  const result = schema.safeParse(data);
  if (!result.success)
    throw new Error('Select a CineTag quality snapshot with a timestamp and check counts.');
  const keys = result.data.checks.map(key);
  if (new Set(keys).size !== keys.length)
    throw new Error('The snapshot contains duplicate check identifiers.');
  return result.data;
}

export async function readSnapshot(file: File): Promise<Quality> {
  if (file.size > 2 * 1024 * 1024) throw new Error('Choose a snapshot smaller than 2 MiB.');
  return parseSnapshot(await file.text());
}

export function compareSnapshots(baseline: Quality, current: Quality): Change[] {
  const old = new Map(baseline.checks.map((check) => [key(check), check]));
  const latest = new Map(current.checks.map((check) => [key(check), check]));
  const changes: Change[] = [];
  for (const id of new Set([...old.keys(), ...latest.keys()])) {
    const previous = old.get(id);
    const next = latest.get(id);
    const before = previous?.count ?? null;
    const after = next?.count ?? null;
    const delta = before !== null && after !== null ? after - before : null;
    let trend: Trend = 'unchanged';
    if (before === null) trend = 'added';
    else if (after === null) trend = 'removed';
    else if (after > before) trend = 'increased';
    else if (after < before) trend = 'improved';
    const source = (next || previous)!;
    changes.push({
      key: id,
      label: source.label,
      dataset: source.dataset_label,
      current: next ?? null,
      before,
      after,
      delta,
      trend,
    });
  }
  return changes.sort(
    (a, b) => a.dataset.localeCompare(b.dataset) || a.label.localeCompare(b.label),
  );
}
