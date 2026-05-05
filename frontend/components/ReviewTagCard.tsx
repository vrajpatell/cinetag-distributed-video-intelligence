'use client';

import { useState } from 'react';
import type { ReviewItem } from '@/lib/types';
import { formatRelativeTime } from '@/lib/format';

type Decision = 'pending' | 'approved' | 'rejected' | 'edited';

export default function ReviewTagCard({
  item,
  onDecision,
}: {
  item: ReviewItem;
  onDecision?: (id: ReviewItem['id'], decision: Decision, value?: string) => void;
}) {
  const [decision, setDecision] = useState<Decision>(
    item.status === 'approved' ? 'approved' : item.status === 'rejected' ? 'rejected' : 'pending'
  );
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(item.tag_value);

  const apply = (d: Decision, v?: string) => {
    setDecision(d);
    onDecision?.(item.id, d, v);
  };

  const conf = Math.round(item.confidence * 100);
  const confColor =
    conf >= 85 ? 'text-emerald-300' : conf >= 65 ? 'text-amber-300' : 'text-rose-300';

  return (
    <div className="panel-strong relative overflow-hidden p-5">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[10.5px] uppercase tracking-wider text-white/45">
            {item.video_title || `video #${item.video_id}`}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className="text-[11px] uppercase tracking-wider text-white/55">{item.tag_type}</span>
            {!editing ? (
              <span className="text-lg font-semibold text-white">{value}</span>
            ) : (
              <input
                value={value}
                onChange={(e) => setValue(e.target.value)}
                className="rounded-md border border-cinetag-border bg-cinetag-panelMuted px-2 py-1 text-sm text-white outline-none focus:border-cinetag-red/60"
              />
            )}
            <span className={`chip-neutral !text-[10px] font-mono ${confColor}`}>
              conf {conf}%
            </span>
            <span className="chip-neutral !text-[10px]">src: {item.source}</span>
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
        <button
          type="button"
          onClick={() => apply('approved', value)}
          className={[
            'btn !px-3 !py-1.5 !text-xs',
            decision === 'approved'
              ? 'bg-emerald-500/90 text-black hover:bg-emerald-400'
              : 'bg-emerald-500/15 text-emerald-200 ring-1 ring-emerald-500/30 hover:bg-emerald-500/25',
          ].join(' ')}
        >
          Approve
        </button>
        <button
          type="button"
          onClick={() => apply('rejected', value)}
          className={[
            'btn !px-3 !py-1.5 !text-xs',
            decision === 'rejected'
              ? 'bg-rose-500/90 text-white hover:bg-rose-400'
              : 'bg-rose-500/15 text-rose-200 ring-1 ring-rose-500/30 hover:bg-rose-500/25',
          ].join(' ')}
        >
          Reject
        </button>
        <button
          type="button"
          onClick={() => {
            if (editing) {
              apply('edited', value);
            }
            setEditing((v) => !v);
          }}
          className="btn !px-3 !py-1.5 !text-xs bg-white/5 text-white/85 ring-1 ring-white/10 hover:bg-white/10"
        >
          {editing ? 'Save edit' : 'Edit value'}
        </button>
        {decision !== 'pending' ? (
          <span className="ml-auto text-[11px] text-white/55">decision: {decision}</span>
        ) : null}
      </div>
    </div>
  );
}
