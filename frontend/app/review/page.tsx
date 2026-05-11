'use client';

import { useEffect, useMemo, useState } from 'react';
import ReviewTagCard from '@/components/ReviewTagCard';
import EmptyState from '@/components/EmptyState';
import ErrorToast, { type ErrorDetail } from '@/components/ErrorToast';
import { ApiError, getReviewItems, patchTag } from '@/lib/api';
import { DEMO_REVIEW_ITEMS } from '@/lib/demo-data';
import type { ReviewItem } from '@/lib/types';

type Decision = 'approved' | 'rejected' | 'edited';
type DecisionState = Decision | 'pending';

const DECISION_TO_TAG_STATUS: Record<Decision, 'approved' | 'rejected'> = {
  approved: 'approved',
  rejected: 'rejected',
  edited: 'approved',
};

export default function ReviewPage() {
  const [items, setItems] = useState<ReviewItem[] | null>(null);
  const [usedDemo, setUsedDemo] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<ErrorDetail | null>(null);
  const [filterType, setFilterType] = useState<string>('all');
  const [filterSource, setFilterSource] = useState<string>('all');
  const [decisions, setDecisions] = useState<Record<string, DecisionState>>({});

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const real = await getReviewItems({ page_size: 100 });
        if (cancelled) return;
        if (real.items.length > 0) {
          setItems(real.items);
          setUsedDemo(false);
        } else {
          setItems(DEMO_REVIEW_ITEMS);
          setUsedDemo(true);
        }
      } catch (err) {
        if (cancelled) return;
        setItems(DEMO_REVIEW_ITEMS);
        setUsedDemo(true);
        setLoadError(err instanceof ApiError ? err.message : 'Could not reach review API.');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const list = items || [];
    return list.filter((i) => {
      if (filterType !== 'all' && i.tag_type !== filterType) return false;
      if (filterSource !== 'all' && i.source !== filterSource) return false;
      return true;
    });
  }, [items, filterType, filterSource]);

  const onDecision = async (
    id: ReviewItem['id'],
    decision: Decision,
    value?: string,
  ) => {
    setDecisions((p) => ({ ...p, [String(id)]: decision }));
    // Demo IDs (strings, prefixed `rv-`) live only in the UI and never hit the API.
    if (typeof id !== 'number') return;
    try {
      await patchTag(id, {
        status: DECISION_TO_TAG_STATUS[decision],
        tag_value: decision === 'edited' ? value : undefined,
      });
      setActionError(null);
    } catch (err) {
      // Roll the optimistic decision back so the UI stays honest.
      setDecisions((p) => {
        const next = { ...p };
        delete next[String(id)];
        return next;
      });
      if (err instanceof ApiError) {
        setActionError({
          title: 'Could not record review decision',
          message: `Tag #${id}: ${err.message}`,
          endpoint: err.endpoint,
          status: err.status,
          hint: 'Try again, or check that PATCH /api/tags/:id is reachable.',
        });
      } else {
        setActionError({
          title: 'Could not record review decision',
          message: err instanceof Error ? err.message : 'Unknown error',
        });
      }
    }
  };

  const batchApproveAll = () => {
    for (const i of filtered) onDecision(i.id, 'approved', i.tag_value);
  };

  const counts = useMemo(() => {
    const list = items || [];
    return {
      total: list.length,
      pending: list.filter((i) => (decisions[String(i.id)] ?? 'pending') === 'pending').length,
      approved: list.filter((i) => decisions[String(i.id)] === 'approved').length,
      rejected: list.filter((i) => decisions[String(i.id)] === 'rejected').length,
    };
  }, [items, decisions]);

  return (
    <div className="mx-auto max-w-[1400px] space-y-6 px-5 py-8">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <span className="chip-violet !text-[11px]">
            <span className="h-1.5 w-1.5 rounded-full bg-violet-400 animate-pulseSoft" />
            Human-in-the-loop review
          </span>
          <h1 className="mt-2 text-3xl font-extrabold tracking-tight md:text-4xl">AI tag review</h1>
          <p className="mt-1 max-w-2xl text-sm text-white/60">
            Approve, reject, or edit AI-generated metadata before it goes live in search and
            recommendations. Each decision writes to the audit log.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="chip-neutral">total {counts.total}</span>
          <span className="chip-emerald">approved {counts.approved}</span>
          <span className="chip-rose">rejected {counts.rejected}</span>
          <span className="chip-amber">pending {counts.pending}</span>
          <button onClick={batchApproveAll} className="btn-primary !px-3 !py-1.5 !text-xs">
            Batch approve filtered
          </button>
        </div>
      </header>

      {loadError ? (
        <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-[12.5px] text-amber-200">
          {loadError}
        </div>
      ) : null}

      <ErrorToast error={actionError} onDismiss={() => setActionError(null)} />


      <div className="panel flex flex-wrap items-center gap-3 p-3">
        <FilterSelect label="Tag type" value={filterType} onChange={setFilterType} options={[
          'all', 'genre', 'mood', 'object', 'scene', 'theme', 'moderation', 'entity',
        ]} />
        <FilterSelect label="Source" value={filterSource} onChange={setFilterSource} options={[
          'all', 'llm', 'transcript', 'visual_frame', 'metadata', 'manual',
        ]} />
        <span className="ml-auto text-[11px] text-white/50">{filtered.length} items</span>
      </div>

      {!items ? (
        <div className="panel p-6 text-sm text-white/55">Loading review queue…</div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title="Review queue is empty"
          description="No tags pending review. New AI tags will appear here as the worker pipeline produces them."
          action={{ label: 'Upload video', href: '/upload' }}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {filtered.map((i) => (
            <ReviewTagCard key={String(i.id)} item={i} onDecision={onDecision} />
          ))}
        </div>
      )}

      {usedDemo ? (
        <div className="rounded-md border border-cinetag-border/70 bg-cinetag-panelMuted/60 px-3 py-2 text-[12px] text-white/55">
          Showing demo review items because the live review queue is empty or unavailable.
        </div>
      ) : null}
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <label className="flex items-center gap-2 text-[12px] text-white/65">
      <span className="text-white/45">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-white/10 bg-cinetag-panelMuted/80 px-2 py-1 text-white outline-none focus:border-cinetag-red/60"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}
