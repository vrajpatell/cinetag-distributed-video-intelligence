'use client';

import { useMemo, useState } from 'react';
import ReviewTagCard from '@/components/ReviewTagCard';
import EmptyState from '@/components/EmptyState';
import { FadeIn, StaggerChildren, StaggerItem } from '@/components/motion/Motion';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { usePatchTag, useReviewItems, type TagDecision } from '@/lib/hooks/use-review';
import type { ReviewItem } from '@/lib/types';

type DecisionState = TagDecision | 'pending';

export default function ReviewPage() {
  const { data, isLoading } = useReviewItems(100);
  const patchTag = usePatchTag();
  const [filterType, setFilterType] = useState<string>('all');
  const [filterSource, setFilterSource] = useState<string>('all');
  const [decisions, setDecisions] = useState<Record<string, DecisionState>>({});

  const items = data?.items ?? null;
  const usedDemo = data?.usedDemo ?? false;
  const loadError = data?.loadError ?? null;

  const filtered = useMemo(() => {
    const list = items || [];
    return list.filter((i) => {
      if (filterType !== 'all' && i.tag_type !== filterType) return false;
      if (filterSource !== 'all' && i.source !== filterSource) return false;
      return true;
    });
  }, [items, filterType, filterSource]);

  const onDecision = (id: ReviewItem['id'], decision: TagDecision, value?: string) => {
    setDecisions((p) => ({ ...p, [String(id)]: decision }));
    patchTag.mutate({ id, decision, value });
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
      <FadeIn>
        <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <Badge variant="violet" className="!text-[11px]">
              <span className="h-1.5 w-1.5 rounded-full bg-violet-400 animate-pulseSoft" />
              Human-in-the-loop review
            </Badge>
            <h1 className="mt-2 text-3xl font-extrabold tracking-tight md:text-4xl">AI tag review</h1>
            <p className="mt-1 max-w-2xl text-sm text-white/60">
              Approve, reject, or edit AI-generated metadata before it goes live in search and
              recommendations. Each decision writes to the audit log.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge>total {counts.total}</Badge>
            <Badge variant="emerald">approved {counts.approved}</Badge>
            <Badge variant="rose">rejected {counts.rejected}</Badge>
            <Badge variant="amber">pending {counts.pending}</Badge>
            <Button size="sm" onClick={batchApproveAll} className="!text-xs">
              Batch approve filtered
            </Button>
          </div>
        </header>
      </FadeIn>

      {loadError ? (
        <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-[12.5px] text-amber-200">
          {loadError}
        </div>
      ) : null}

      <div className="panel flex flex-wrap items-center gap-4 p-3">
        <FilterSelect
          label="Tag type"
          value={filterType}
          onChange={setFilterType}
          options={['all', 'genre', 'mood', 'object', 'scene', 'theme', 'moderation', 'entity']}
        />
        <FilterSelect
          label="Source"
          value={filterSource}
          onChange={setFilterSource}
          options={['all', 'llm', 'transcript', 'visual_frame', 'metadata', 'manual']}
        />
        <span className="ml-auto text-[11px] text-white/50">{filtered.length} items</span>
      </div>

      {isLoading ? (
        <div className="panel p-6 text-sm text-white/55">Loading review queue…</div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title="Review queue is empty"
          description="No tags pending review. New AI tags will appear here as the worker pipeline produces them."
          action={{ label: 'Upload video', href: '/upload' }}
        />
      ) : (
        <StaggerChildren className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {filtered.map((i) => (
            <StaggerItem key={String(i.id)}>
              <ReviewTagCard item={i} onDecision={onDecision} />
            </StaggerItem>
          ))}
        </StaggerChildren>
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
    <div className="flex items-center gap-2">
      <Label className="text-white/45">{label}</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="w-[160px] !h-8 !text-[12px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o} value={o}>
              {o}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
