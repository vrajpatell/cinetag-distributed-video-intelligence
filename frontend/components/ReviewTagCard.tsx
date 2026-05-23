'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Check, Pencil, X } from 'lucide-react';
import type { ReviewItem } from '@/lib/types';
import { formatRelativeTime } from '@/lib/format';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

export type ReviewDecision = 'approved' | 'rejected' | 'edited';
type LocalDecisionState = ReviewDecision | 'pending';

const editSchema = z.object({
  tag_value: z.string().min(1, 'Tag value is required').max(120, 'Tag value is too long'),
});

type EditFormValues = z.infer<typeof editSchema>;

export default function ReviewTagCard({
  item,
  onDecision,
}: {
  item: ReviewItem;
  onDecision?: (id: ReviewItem['id'], decision: ReviewDecision, value?: string) => void;
}) {
  const [decision, setDecision] = useState<LocalDecisionState>(
    item.status === 'approved' ? 'approved' : item.status === 'rejected' ? 'rejected' : 'pending',
  );
  const [editing, setEditing] = useState(false);

  const form = useForm<EditFormValues>({
    resolver: zodResolver(editSchema),
    defaultValues: { tag_value: item.tag_value },
  });

  const apply = (d: ReviewDecision, v?: string) => {
    setDecision(d);
    onDecision?.(item.id, d, v);
  };

  const onSaveEdit = form.handleSubmit((values) => {
    apply('edited', values.tag_value);
    setEditing(false);
  });

  const conf = Math.round(item.confidence * 100);
  const confVariant = conf >= 85 ? 'emerald' : conf >= 65 ? 'amber' : 'rose';

  return (
    <div className="panel-strong relative overflow-hidden p-5 transition-colors hover:border-white/15">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[10.5px] uppercase tracking-wider text-white/45">
            {item.video_title || `video #${item.video_id}`}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className="text-[11px] uppercase tracking-wider text-white/55">{item.tag_type}</span>
            {!editing ? (
              <span className="text-lg font-semibold text-white">{form.watch('tag_value')}</span>
            ) : (
              <form onSubmit={onSaveEdit} className="flex items-center gap-2">
                <Input
                  {...form.register('tag_value')}
                  className="!h-8 !text-sm max-w-[220px]"
                  autoFocus
                />
                {form.formState.errors.tag_value ? (
                  <span className="text-[10px] text-rose-300">
                    {form.formState.errors.tag_value.message}
                  </span>
                ) : null}
              </form>
            )}
            <Badge variant={confVariant as 'emerald' | 'amber' | 'rose'} className="!text-[10px] font-mono">
              conf {conf}%
            </Badge>
            <Badge className="!text-[10px]">src: {item.source}</Badge>
          </div>
        </div>
        <div className="text-[11px] text-white/45">{formatRelativeTime(item.created_at)}</div>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
        {item.rationale ? (
          <div className="panel-muted p-3">
            <div className="text-[10.5px] uppercase tracking-wider text-white/50">Why this tag</div>
            <p className="mt-1 text-[12.5px] text-white/75">{item.rationale}</p>
          </div>
        ) : null}
        {item.transcript_snippet ? (
          <div className="panel-muted p-3">
            <div className="text-[10.5px] uppercase tracking-wider text-white/50">Transcript snippet</div>
            <p className="mt-1 text-[12.5px] italic text-white/75">{item.transcript_snippet}</p>
          </div>
        ) : null}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant={decision === 'approved' ? 'success' : 'secondary'}
          onClick={() => apply('approved', form.getValues('tag_value'))}
          className={cn(
            '!text-xs',
            decision !== 'approved' &&
              '!bg-emerald-500/15 !text-emerald-200 !border-emerald-500/30 hover:!bg-emerald-500/25',
          )}
        >
          <Check className="h-3.5 w-3.5" />
          Approve
        </Button>
        <Button
          type="button"
          size="sm"
          variant={decision === 'rejected' ? 'destructive' : 'secondary'}
          onClick={() => apply('rejected', form.getValues('tag_value'))}
          className={cn(
            '!text-xs',
            decision !== 'rejected' &&
              '!bg-rose-500/15 !text-rose-200 !border-rose-500/30 hover:!bg-rose-500/25',
          )}
        >
          <X className="h-3.5 w-3.5" />
          Reject
        </Button>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={() => {
            if (editing) {
              void onSaveEdit();
            } else {
              setEditing(true);
            }
          }}
          className="!text-xs"
        >
          <Pencil className="h-3.5 w-3.5" />
          {editing ? 'Save edit' : 'Edit value'}
        </Button>
        {decision !== 'pending' ? (
          <span className="ml-auto text-[11px] text-white/55">decision: {decision}</span>
        ) : null}
      </div>
    </div>
  );
}
