import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, ChevronRight, Pencil, ThumbsDown, ThumbsUp } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { Modal } from '@/components/ui/Modal';
import { cn } from '@/lib/cn';
import { useReviewQueue, type ReviewItem } from '@/state/hooks/useReviewQueue';
import { usePatchTag } from '@/state/hooks/useTags';
import { formatRelative } from '@/lib/format';
import { toast } from '@/components/ui/toastStore';

const TAG_TYPES = ['all', 'topic', 'genre', 'mood', 'object', 'person', 'scene'];

export default function ReviewQueuePage(): JSX.Element {
  const queueQ = useReviewQueue();
  const patch = usePatchTag();

  const [filterType, setFilterType] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [activeId, setActiveId] = useState<number | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [editFor, setEditFor] = useState<ReviewItem | null>(null);
  const [editValue, setEditValue] = useState('');
  const editInputRef = useRef<HTMLInputElement | null>(null);

  const items = useMemo(() => {
    const list = queueQ.data ?? [];
    return list.filter((it) => {
      if (filterType !== 'all' && it.tag.tag_type !== filterType) return false;
      if (search.trim()) {
        const q = search.toLowerCase();
        if (
          !it.tag.tag_value.toLowerCase().includes(q) &&
          !(it.video.title ?? it.video.original_filename).toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      return true;
    });
  }, [queueQ.data, filterType, search]);

  useEffect(() => {
    if (activeId != null && items.find((i) => i.tag.id === activeId)) return;
    setActiveId(items[0]?.tag.id ?? null);
  }, [items, activeId]);

  const active = useMemo(() => items.find((i) => i.tag.id === activeId) ?? null, [items, activeId]);

  const moveActive = useCallback(
    (delta: 1 | -1) => {
      const idx = items.findIndex((i) => i.tag.id === activeId);
      if (idx === -1) return;
      const next = items[Math.min(items.length - 1, Math.max(0, idx + delta))];
      if (next) setActiveId(next.tag.id);
    },
    [items, activeId],
  );

  const approve = useCallback(
    (item: ReviewItem) =>
      patch.mutate(
        { tagId: item.tag.id, videoId: item.video.id, status: 'approved' },
        { onSuccess: () => toast.success('Approved', `${item.tag.tag_type}: ${item.tag.tag_value}`) },
      ),
    [patch],
  );

  const reject = useCallback(
    (item: ReviewItem) =>
      patch.mutate(
        { tagId: item.tag.id, videoId: item.video.id, status: 'rejected' },
        { onSuccess: () => toast.info('Rejected', `${item.tag.tag_type}: ${item.tag.tag_value}`) },
      ),
    [patch],
  );

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) return;
      if (editFor) return;
      if (!active) return;
      if (e.key === 'a' || e.key === 'A') {
        e.preventDefault();
        approve(active);
        moveActive(1);
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        reject(active);
        moveActive(1);
      } else if (e.key === 'j' || e.key === 'J' || e.key === 'ArrowDown') {
        e.preventDefault();
        moveActive(1);
      } else if (e.key === 'k' || e.key === 'K' || e.key === 'ArrowUp') {
        e.preventDefault();
        moveActive(-1);
      } else if (e.key === 'e' || e.key === 'E') {
        e.preventDefault();
        setEditFor(active);
        setEditValue(active.tag.tag_value);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [active, approve, reject, moveActive, editFor]);

  const toggleSelected = (tagId: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(tagId)) next.delete(tagId);
      else next.add(tagId);
      return next;
    });
  };

  const bulkApply = (status: 'approved' | 'rejected') => {
    if (selected.size === 0) return;
    const list = items.filter((i) => selected.has(i.tag.id));
    list.forEach((it) => patch.mutate({ tagId: it.tag.id, videoId: it.video.id, status }));
    toast.success(
      `Bulk ${status === 'approved' ? 'approve' : 'reject'}`,
      `${list.length} tag${list.length === 1 ? '' : 's'} queued`,
    );
    setSelected(new Set());
  };

  const submitEdit = () => {
    if (!editFor) return;
    const value = editValue.trim();
    if (!value) return;
    patch.mutate(
      { tagId: editFor.tag.id, videoId: editFor.video.id, tag_value: value, status: 'approved' },
      {
        onSuccess: () => {
          toast.success('Tag updated', `${editFor.tag.tag_type}: ${value}`);
          setEditFor(null);
          moveActive(1);
        },
      },
    );
  };

  return (
    <div className="mx-auto max-w-rail px-4 pb-24 pt-8 sm:px-6 lg:px-12">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold tracking-tightest text-text-0 sm:text-4xl">
            Review queue
          </h1>
          <p className="mt-1 text-sm text-text-1">
            Approve or reject AI-generated tags. {items.length} pending.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            aria-label="Filter by tag type"
            className="rounded-md border border-bg-3 bg-bg-1 px-3 py-1.5 text-xs text-text-0 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent"
          >
            {TAG_TYPES.map((t) => (
              <option key={t} value={t} className="bg-bg-1">
                {t}
              </option>
            ))}
          </select>
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter…"
            aria-label="Filter tags"
            className="w-48 rounded-md border border-bg-3 bg-bg-1 px-3 py-1.5 text-xs text-text-0 placeholder:text-text-2 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>
      </header>

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(280px,400px)_1fr]">
        <Card className="overflow-hidden p-0">
          <div className="border-b border-bg-3 px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.15em] text-text-2">
            Pending tags
          </div>
          {queueQ.isLoading ? (
            <ul>
              {Array.from({ length: 6 }).map((_, i) => (
                <li key={i} className="border-t border-bg-3 px-4 py-3">
                  <Skeleton className="h-10 w-full" />
                </li>
              ))}
            </ul>
          ) : queueQ.isError ? (
            <p role="alert" className="px-4 py-8 text-sm text-accent">
              Failed to load: {(queueQ.error as Error).message}
            </p>
          ) : items.length === 0 ? (
            <p className="px-4 py-12 text-center text-sm text-text-2">
              All caught up — no tags awaiting review.
            </p>
          ) : (
            <ul role="listbox" aria-label="Pending tags" className="max-h-[70vh] overflow-y-auto">
              {items.map((item) => {
                const isActive = item.tag.id === activeId;
                const isSelected = selected.has(item.tag.id);
                return (
                  <li key={item.tag.id} className="border-t border-bg-3">
                    <div
                      className={cn(
                        'flex w-full items-start gap-3 px-3 py-3 text-left transition-colors',
                        isActive ? 'bg-bg-2' : 'hover:bg-bg-2',
                      )}
                    >
                      <input
                        type="checkbox"
                        aria-label={`Select tag ${item.tag.tag_value}`}
                        checked={isSelected}
                        onChange={() => toggleSelected(item.tag.id)}
                        className="mt-1 h-4 w-4 cursor-pointer accent-[#e50914]"
                      />
                      <button
                        type="button"
                        onClick={() => setActiveId(item.tag.id)}
                        className="min-w-0 flex-1 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                      >
                        <p className="line-clamp-1 text-sm font-medium text-text-0">
                          {item.tag.tag_value}
                        </p>
                        <p className="mt-0.5 line-clamp-1 text-xs text-text-2">
                          <span className="uppercase tracking-wider">{item.tag.tag_type}</span>
                          <span className="mx-1.5">·</span>
                          {item.video.title ?? item.video.original_filename}
                        </p>
                      </button>
                      <span className="text-[10px] text-text-2">
                        {Math.round((item.tag.confidence ?? 0) * 100)}%
                      </span>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        <Card className="p-6">
          {!active ? (
            <p className="text-sm text-text-2">Select a tag to review.</p>
          ) : (
            <article>
              <p className="text-xs font-mono text-text-2">TAG #{active.tag.id}</p>
              <h2 className="mt-1 font-display text-2xl font-bold tracking-tight text-text-0">
                {active.tag.tag_value}
              </h2>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                <Badge tone="neutral">
                  <span className="uppercase tracking-wider">{active.tag.tag_type}</span>
                </Badge>
                <Badge tone="warning">Pending review</Badge>
                {active.tag.confidence != null && (
                  <Badge
                    tone={
                      active.tag.confidence >= 0.85
                        ? 'success'
                        : active.tag.confidence >= 0.6
                          ? 'warning'
                          : 'danger'
                    }
                  >
                    Confidence {Math.round(active.tag.confidence * 100)}%
                  </Badge>
                )}
                <span className="text-text-2">{formatRelative(active.tag.created_at)}</span>
              </div>

              <section className="mt-6 rounded-md border border-bg-3 bg-bg-2 p-4">
                <p className="text-xs uppercase tracking-wider text-text-2">Source video</p>
                <Link
                  to={`/videos/${active.video.id}`}
                  className="mt-1 inline-flex items-center gap-2 text-sm font-semibold text-text-0 hover:text-accent"
                >
                  {active.video.title ?? active.video.original_filename}
                  <ChevronRight className="h-4 w-4" aria-hidden />
                </Link>
              </section>

              {active.tag.rationale && (
                <section className="mt-4 rounded-md border border-bg-3 bg-bg-1 p-4">
                  <p className="text-xs uppercase tracking-wider text-text-2">Rationale</p>
                  <p className="mt-1 text-sm text-text-0">{active.tag.rationale}</p>
                </section>
              )}

              <div className="mt-6 flex flex-wrap items-center gap-2">
                <Button
                  variant="primary"
                  iconLeft={<ThumbsUp className="h-4 w-4" aria-hidden />}
                  onClick={() => {
                    approve(active);
                    moveActive(1);
                  }}
                >
                  Approve
                </Button>
                <Button
                  variant="danger"
                  iconLeft={<ThumbsDown className="h-4 w-4" aria-hidden />}
                  onClick={() => {
                    reject(active);
                    moveActive(1);
                  }}
                >
                  Reject
                </Button>
                <Button
                  variant="ghost"
                  iconLeft={<Pencil className="h-4 w-4" aria-hidden />}
                  onClick={() => {
                    setEditFor(active);
                    setEditValue(active.tag.tag_value);
                  }}
                >
                  Edit value
                </Button>
                <Button variant="ghost" onClick={() => moveActive(1)}>
                  Skip
                </Button>
              </div>
            </article>
          )}
        </Card>
      </div>

      <KeyLegend />

      {selected.size > 0 && (
        <div
          role="region"
          aria-label="Bulk actions"
          className="fixed inset-x-0 bottom-0 z-30 flex items-center justify-center gap-3 border-t border-bg-3 bg-bg-1/95 px-4 py-3 backdrop-blur"
        >
          <span className="text-xs text-text-1">{selected.size} selected</span>
          <Button
            size="sm"
            variant="primary"
            iconLeft={<Check className="h-4 w-4" aria-hidden />}
            onClick={() => bulkApply('approved')}
          >
            Approve all
          </Button>
          <Button
            size="sm"
            variant="danger"
            iconLeft={<ThumbsDown className="h-4 w-4" aria-hidden />}
            onClick={() => bulkApply('rejected')}
          >
            Reject all
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>
            Clear
          </Button>
        </div>
      )}

      <Modal
        open={!!editFor}
        onClose={() => setEditFor(null)}
        title="Edit tag value"
        description="The tag will be marked approved with the new value."
        initialFocusRef={editInputRef}
      >
        <div className="space-y-4">
          <div>
            <label htmlFor="edit-value" className="mb-1 block text-xs font-medium text-text-1">
              Value
            </label>
            <input
              id="edit-value"
              ref={editInputRef}
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              className="w-full rounded-md border border-bg-3 bg-bg-2 px-3 py-2 text-sm text-text-0 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent"
              onKeyDown={(e) => {
                if (e.key === 'Enter') submitEdit();
              }}
            />
          </div>
          <div className="flex items-center justify-end gap-2">
            <Button variant="ghost" onClick={() => setEditFor(null)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={submitEdit} disabled={!editValue.trim()}>
              Save & approve
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function KeyLegend(): JSX.Element {
  const items: Array<[string, string]> = [
    ['A', 'Approve'],
    ['R', 'Reject'],
    ['E', 'Edit value'],
    ['J / ↓', 'Next'],
    ['K / ↑', 'Previous'],
  ];
  return (
    <aside className="mt-8 flex flex-wrap items-center gap-3 text-xs text-text-2">
      <span className="font-semibold uppercase tracking-wider">Keys:</span>
      {items.map(([k, label]) => (
        <span key={k} className="inline-flex items-center gap-1">
          <kbd className="rounded border border-bg-3 bg-bg-1 px-1.5 py-0.5 font-mono text-[11px] text-text-0">
            {k}
          </kbd>
          <span>{label}</span>
        </span>
      ))}
    </aside>
  );
}
