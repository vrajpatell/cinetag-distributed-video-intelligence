'use client';

import { useState, type FormEvent } from 'react';
import { inputClass } from '@/lib/catalog/format';
import {
  needsValue,
  operators,
  type Dataset,
  type Filter,
  type Operator,
  type View,
} from '@/lib/catalog/types';

interface Props {
  dataset: Dataset;
  view: View;
  update: (view: View) => void;
}

export default function FilterBar({ dataset, view, update }: Props) {
  const [search, setSearch] = useState(view.search);
  const [fieldKey, setFieldKey] = useState(dataset.fields[0].id);
  const field = dataset.fields.find((item) => item.id === fieldKey)!;
  const [operator, setOperator] = useState<Operator>('eq');
  const [operand, setOperand] = useState('');

  function addFilter(event: FormEvent) {
    event.preventDefault();
    if (view.filters.length >= 12) return;
    const rule: Filter = { field: field.id, operator };
    if (needsValue(operator)) {
      if (!operand.trim()) return;
      rule.value = operand;
    }
    update({ ...view, filters: [...view.filters, rule] });
    setOperand('');
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <form
          className="flex flex-1 items-end gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            update({ ...view, search: search.trim() });
          }}
        >
          <label className="min-w-0 flex-1 text-sm">
            Search {dataset.label.toLowerCase()}
            <input
              className={`${inputClass} mt-1 w-full`}
              type="search"
              maxLength={256}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <button className="btn-secondary" type="submit">
            Search
          </button>
        </form>
        <label className="text-sm">
          Preset
          <select
            className={`${inputClass} mt-1 block max-w-full`}
            value={view.preset || ''}
            onChange={(event) => update({ ...view, preset: event.target.value || null })}
          >
            <option value="">All records</option>
            {dataset.presets.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {view.preset && (
        <p className="text-sm text-white/65">
          {dataset.presets.find((p) => p.id === view.preset)?.description}
        </p>
      )}
      <details className="rounded-lg border border-white/10 p-3">
        <summary className="cursor-pointer text-sm font-medium">Filter by field</summary>
        <form className="mt-3 flex flex-wrap items-end gap-2" onSubmit={addFilter}>
          <label className="text-xs">
            Field
            <select
              className={`${inputClass} mt-1 block`}
              value={fieldKey}
              onChange={(event) => {
                setFieldKey(event.target.value);
                setOperator('eq');
                setOperand('');
              }}
            >
              {dataset.fields.map((col) => (
                <option key={col.id} value={col.id}>
                  {col.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs">
            Condition
            <select
              className={`${inputClass} mt-1 block`}
              value={operator}
              onChange={(event) => setOperator(event.target.value as Operator)}
            >
              {field.operators.map((op) => (
                <option key={op} value={op}>
                  {operators[op]}
                </option>
              ))}
            </select>
          </label>
          {needsValue(operator) && (
            <label className="text-xs">
              {field.kind === 'datetime' ? 'Date and time (UTC)' : 'Value'}
              <input
                className={`${inputClass} mt-1 block`}
                required
                maxLength={512}
                type={
                  field.kind === 'datetime'
                    ? 'datetime-local'
                    : field.kind === 'text'
                      ? 'text'
                      : 'number'
                }
                step={['integer', 'milliseconds', 'bytes'].includes(field.kind) ? '1' : 'any'}
                value={operand}
                onChange={(event) => setOperand(event.target.value)}
              />
            </label>
          )}
          <button type="submit" className="btn-secondary" disabled={view.filters.length >= 12}>
            Add filter
          </button>
        </form>
      </details>
      {(view.search || view.filters.length > 0) && (
        <div className="flex flex-wrap gap-2">
          {view.search && (
            <button
              className="chip-neutral"
              aria-label="Remove search"
              onClick={() => {
                setSearch('');
                update({ ...view, search: '' });
              }}
            >
              Search · {view.search} ×
            </button>
          )}
          {view.filters.map((rule, index) => {
            const label = dataset.fields.find((col) => col.id === rule.field)?.label;
            const text = [label, operators[rule.operator], rule.value].filter(Boolean).join(' ');
            return (
              <button
                key={index}
                className="chip-neutral"
                aria-label={`Remove filter: ${text}`}
                onClick={() =>
                  update({ ...view, filters: view.filters.filter((_, i) => i !== index) })
                }
              >
                {text} ×
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
