'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  compareVideos,
  type AssetRef,
  type Comparison,
  type LabelMatch,
} from '@/lib/catalog/compare';
import { displayCell } from '@/lib/catalog/format';
import AssetPicker from './AssetPicker';

function percentage(value: number | null) {
  return value == null ? 'Unavailable' : `${(value * 100).toFixed(1)}%`;
}

function TagList({ label, tags }: { label: string; tags: LabelMatch[] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold">
        {label} ({tags.length})
      </h3>
      {tags.length ? (
        <ul className="mt-2 flex max-h-56 flex-wrap gap-1 overflow-y-auto">
          {tags.map((tag) => (
            <li key={JSON.stringify(tag)} className="chip-neutral">
              {tag.type} · {tag.value}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1 text-sm text-white/55">None</p>
      )}
    </div>
  );
}

function ComparisonResults({ data }: { data: Comparison }) {
  const [differences, setDifferences] = useState(false);
  const shown = data.metrics.filter(
    (m) => !differences || ['different', 'left_only', 'right_only'].includes(m.relation),
  );
  return (
    <div className="space-y-4">
      <section className="panel-strong space-y-3 p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold">Media and analysis</h2>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={differences}
              onChange={(e) => setDifferences(e.target.checked)}
            />{' '}
            Differences only
          </label>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr>
                <th className="p-2">Measurement</th>
                {[data.left, data.right].map((asset) => (
                  <th className="p-2" key={asset.id}>
                    <Link className="underline" href={`/videos/${asset.id}`}>
                      {asset.title}
                    </Link>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {shown.map((metric) => (
                <tr key={metric.id} className="border-t border-white/10">
                  <th scope="row" className="p-2 font-normal">
                    <span className="block text-xs text-white/45">{metric.group}</span>
                    {metric.label}
                  </th>
                  <td className="p-2">{displayCell(metric.left, metric.kind)}</td>
                  <td className="p-2">{displayCell(metric.right, metric.kind)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!shown.length && <p>No differing measurements.</p>}
      </section>
      <section className="panel-strong space-y-4 p-5">
        <h2 className="font-semibold">Approved tag overlap · {percentage(data.tags.similarity)}</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <TagList label="Shared" tags={data.tags.shared} />
          <TagList label={`Only in ${data.left.title}`} tags={data.tags.left_only} />
          <TagList label={`Only in ${data.right.title}`} tags={data.tags.right_only} />
        </div>
      </section>
      <section className="panel-strong space-y-3 p-5">
        <h2 className="font-semibold">
          Transcript vocabulary overlap · {percentage(data.speech.vocabulary_similarity)}
        </h2>
        <p className="text-sm text-white/65">
          {data.speech.shared_words} shared distinct words · {data.speech.unique_left} in the first
          transcript · {data.speech.unique_right} in the second
        </p>
        {data.speech.frequent_shared.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <caption className="pb-2 text-left">Most frequent shared words</caption>
              <thead>
                <tr>
                  <th>Word</th>
                  <th>{data.left.title}</th>
                  <th>{data.right.title}</th>
                </tr>
              </thead>
              <tbody>
                {data.speech.frequent_shared.map((item) => (
                  <tr key={item.word} className="border-t border-white/10">
                    <td className="py-1">{item.word}</td>
                    <td>{item.left_count}</td>
                    <td>{item.right_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

export default function CompareVideos({
  initialLeft,
  initialRight,
}: {
  initialLeft: number | null;
  initialRight: number | null;
}) {
  const [left, setLeft] = useState<AssetRef | null>(
    initialLeft ? { id: initialLeft, title: `Video #${initialLeft}` } : null,
  );
  const [right, setRight] = useState<AssetRef | null>(
    initialRight ? { id: initialRight, title: `Video #${initialRight}` } : null,
  );
  const query = useQuery({
    queryKey: ['catalog-compare', left?.id, right?.id],
    queryFn: ({ signal }) => compareVideos(left!.id, right!.id, signal),
    enabled: !!left && !!right && left.id !== right.id,
  });
  function choose(first: AssetRef | null, second: AssetRef | null) {
    setLeft(first);
    setRight(second);
    const params = new URLSearchParams();
    if (first) params.set('left', String(first.id));
    if (second) params.set('right', String(second.id));
    window.history.replaceState(null, '', `/catalog/compare?${params}`);
  }
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2">
        <AssetPicker
          label="First video"
          selected={query.data?.left || left}
          excluded={right?.id}
          onSelect={(asset) => choose(asset, right)}
        />
        <AssetPicker
          label="Second video"
          selected={query.data?.right || right}
          excluded={left?.id}
          onSelect={(asset) => choose(left, asset)}
        />
      </div>
      {left && right && (
        <button className="btn-secondary" onClick={() => choose(right, left)}>
          Swap videos
        </button>
      )}
      {left && right && query.isPending && <p role="status">Comparing videos…</p>}
      {query.isError && (
        <p role="alert">
          {query.error.message}{' '}
          <button onClick={() => query.refetch()} className="underline">
            Retry
          </button>
        </p>
      )}
      {query.data && <ComparisonResults data={query.data} />}
    </div>
  );
}
