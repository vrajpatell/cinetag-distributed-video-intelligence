import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ChevronLeft, Plus } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { Tabs, type TabItem } from '@/components/ui/Tabs';
import { Badge } from '@/components/ui/Badge';
import { TagChip } from '@/components/media/TagChip';
import { PosterFallback } from '@/components/media/MediaCard';
import { useVideo } from '@/state/hooks/useVideos';
import {
  useFrames,
  useScenes,
  useTagsByVideo,
  useTranscript,
} from '@/state/hooks/useVideoDetails';
import { useAddManualTag, usePatchTag } from '@/state/hooks/useTags';
import { humanizeBytes, humanizeDuration } from '@/lib/format';
import type { GeneratedTag } from '@/lib/zodSchemas';

type TabId = 'tags' | 'scenes' | 'transcript' | 'frames';

export default function VideoDetailPage(): JSX.Element {
  const { id } = useParams<{ id: string }>();
  const numericId = id ? Number(id) : undefined;
  const videoQ = useVideo(numericId);
  const [tab, setTab] = useState<TabId>('tags');

  if (videoQ.isLoading) {
    return (
      <div className="mx-auto max-w-rail px-4 py-8 sm:px-6 lg:px-12">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="mt-4 aspect-video w-full" />
      </div>
    );
  }

  if (videoQ.isError || !videoQ.data) {
    return (
      <div className="mx-auto max-w-rail px-4 py-16 text-center sm:px-6 lg:px-12">
        <p className="font-display text-2xl font-bold text-text-0">Video not found</p>
        <p className="mt-2 text-sm text-text-1">{(videoQ.error as Error)?.message ?? 'No video with that id.'}</p>
        <Link to="/" className="mt-4 inline-block">
          <Button variant="ghost" iconLeft={<ChevronLeft className="h-4 w-4" aria-hidden />}>
            Back to browse
          </Button>
        </Link>
      </div>
    );
  }

  const v = videoQ.data;

  const tabs: TabItem[] = [
    { id: 'tags', label: 'Tags' },
    { id: 'scenes', label: 'Scenes' },
    { id: 'transcript', label: 'Transcript' },
    { id: 'frames', label: 'Frames' },
  ];

  return (
    <div className="mx-auto max-w-rail px-4 pb-16 pt-6 sm:px-6 lg:px-12">
      <Link to="/" className="inline-flex items-center gap-1 text-sm text-text-1 hover:text-text-0">
        <ChevronLeft className="h-4 w-4" aria-hidden /> Browse
      </Link>

      <div className="mt-4 grid gap-6 lg:grid-cols-[3fr_2fr]">
        <div className="relative aspect-video w-full overflow-hidden rounded-xl border border-bg-3 bg-bg-2">
          <PosterFallback title={v.title ?? v.original_filename} videoId={v.id} />
          <div className="absolute inset-0 grid place-items-center">
            <div className="rounded-full bg-black/60 p-4 text-white shadow-card backdrop-blur">
              <span className="block h-0 w-0 border-y-[12px] border-l-[20px] border-y-transparent border-l-white" aria-hidden />
            </div>
          </div>
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-4">
            <p className="text-xs font-medium uppercase tracking-wider text-text-2">Preview unavailable</p>
            <p className="text-sm text-text-1">Player will stream from the video storage backend once added.</p>
          </div>
        </div>

        <div>
          <h1 className="font-display text-3xl font-bold tracking-tightest text-text-0 sm:text-4xl">
            {v.title ?? v.original_filename}
          </h1>
          <p className="mt-2 text-sm text-text-1">{v.original_filename}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Badge tone="neutral">
              <span className="capitalize">{v.status}</span>
            </Badge>
          </div>
          <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <MetaRow label="Duration" value={humanizeDuration(v.duration_seconds ?? null)} />
            <MetaRow
              label="Resolution"
              value={v.width && v.height ? `${v.width}×${v.height}` : '—'}
            />
            <MetaRow label="Codec" value={v.codec ?? '—'} />
            <MetaRow label="Bitrate" value={v.bitrate ? `${Math.round(v.bitrate / 1000)} kbps` : '—'} />
            <MetaRow label="Frame rate" value={v.frame_rate ? `${v.frame_rate.toFixed(2)} fps` : '—'} />
            <MetaRow label="Size" value={humanizeBytes(v.file_size_bytes ?? null)} />
            <MetaRow label="Uploaded" value={new Date(v.created_at).toLocaleString()} />
            <MetaRow label="Updated" value={new Date(v.updated_at).toLocaleString()} />
          </dl>
        </div>
      </div>

      <Tabs
        className="mt-10"
        items={tabs}
        value={tab}
        onChange={(id) => setTab(id as TabId)}
      />

      <div className="mt-6">
        {tab === 'tags' && numericId != null && <TagsPanel videoId={numericId} />}
        {tab === 'scenes' && numericId != null && <ScenesPanel videoId={numericId} />}
        {tab === 'transcript' && numericId != null && <TranscriptPanel videoId={numericId} />}
        {tab === 'frames' && numericId != null && <FramesPanel videoId={numericId} />}
      </div>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="flex flex-col">
      <dt className="text-xs uppercase tracking-wider text-text-2">{label}</dt>
      <dd className="text-text-0">{value}</dd>
    </div>
  );
}

function TagsPanel({ videoId }: { videoId: number }): JSX.Element {
  const tagsQ = useTagsByVideo(videoId);
  const patch = usePatchTag();
  const add = useAddManualTag();

  const [type, setType] = useState('topic');
  const [value, setValue] = useState('');

  const grouped = useMemo(() => {
    const map = new Map<string, GeneratedTag[]>();
    for (const t of tagsQ.data ?? []) {
      const arr = map.get(t.tag_type) ?? [];
      arr.push(t);
      map.set(t.tag_type, arr);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [tagsQ.data]);

  return (
    <div className="space-y-6">
      <Card className="p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!value.trim()) return;
            add.mutate(
              { videoId, tag_type: type.trim() || 'topic', tag_value: value.trim() },
              { onSuccess: () => setValue('') },
            );
          }}
          className="flex flex-col gap-3 sm:flex-row sm:items-end"
        >
          <div className="flex-1">
            <label htmlFor="manual-type" className="mb-1 block text-xs font-medium text-text-1">
              Tag type
            </label>
            <input
              id="manual-type"
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full rounded-md border border-bg-3 bg-bg-2 px-3 py-2 text-sm text-text-0 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent"
              placeholder="topic, mood, person…"
            />
          </div>
          <div className="flex-[2]">
            <label htmlFor="manual-value" className="mb-1 block text-xs font-medium text-text-1">
              Value
            </label>
            <input
              id="manual-value"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              className="w-full rounded-md border border-bg-3 bg-bg-2 px-3 py-2 text-sm text-text-0 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent"
              placeholder="add a manual tag"
            />
          </div>
          <Button
            type="submit"
            variant="primary"
            loading={add.isPending}
            disabled={!value.trim()}
            iconLeft={!add.isPending ? <Plus className="h-4 w-4" aria-hidden /> : undefined}
          >
            Add tag
          </Button>
        </form>
      </Card>

      {tagsQ.isLoading ? (
        <Skeleton className="h-32 w-full" />
      ) : tagsQ.isError ? (
        <ErrorBanner message={(tagsQ.error as Error).message} />
      ) : (tagsQ.data ?? []).length === 0 ? (
        <EmptyHint message="No tags yet. The tagging stage will populate this list." />
      ) : (
        <div className="space-y-5">
          {grouped.map(([type, tags]) => (
            <section key={type}>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-text-2">
                {type}
              </h3>
              <div className="flex flex-wrap gap-2">
                {tags.map((t) => (
                  <TagChip
                    key={t.id}
                    tag={t}
                    onApprove={
                      t.status === 'pending_review'
                        ? () => patch.mutate({ tagId: t.id, videoId, status: 'approved' })
                        : undefined
                    }
                    onReject={
                      t.status === 'pending_review'
                        ? () => patch.mutate({ tagId: t.id, videoId, status: 'rejected' })
                        : undefined
                    }
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

function ScenesPanel({ videoId }: { videoId: number }): JSX.Element {
  const q = useScenes(videoId);
  if (q.isLoading) return <Skeleton className="h-40 w-full" />;
  if (q.isError) return <ErrorBanner message={(q.error as Error).message} />;
  const scenes = q.data ?? [];
  if (scenes.length === 0) return <EmptyHint message="No scenes detected for this video yet." />;
  return (
    <ol className="space-y-2">
      {scenes.map((s) => (
        <li key={s.id} className="rounded-md border border-bg-3 bg-bg-1 p-4 transition-colors hover:bg-bg-2">
          <button type="button" className="flex w-full items-start justify-between gap-4 text-left">
            <div className="min-w-0">
              <p className="font-mono text-xs text-text-2">
                {humanizeDuration(s.start_time_seconds)} – {humanizeDuration(s.end_time_seconds)}
              </p>
              <p className="mt-1 line-clamp-3 text-sm text-text-0">{s.summary ?? 'No summary'}</p>
            </div>
            <span className="rounded-full bg-bg-3 px-2 py-1 text-[10px] uppercase tracking-wider text-text-1">
              Seek
            </span>
          </button>
        </li>
      ))}
    </ol>
  );
}

function TranscriptPanel({ videoId }: { videoId: number }): JSX.Element {
  const q = useTranscript(videoId);
  if (q.isLoading) return <Skeleton className="h-64 w-full" />;
  if (q.isError) return <ErrorBanner message={(q.error as Error).message} />;
  const t = q.data;
  if (!t) return <EmptyHint message="No transcript available yet." />;
  return (
    <Card className="p-6">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {t.language && <Badge tone="neutral">Lang: {t.language}</Badge>}
        {t.confidence != null && (
          <Badge tone={t.confidence >= 0.85 ? 'success' : t.confidence >= 0.6 ? 'warning' : 'danger'}>
            Confidence: {Math.round(t.confidence * 100)}%
          </Badge>
        )}
      </div>
      <div className="prose prose-invert max-h-[60vh] max-w-none overflow-y-auto whitespace-pre-wrap text-sm leading-relaxed text-text-0">
        {t.text}
      </div>
    </Card>
  );
}

function FramesPanel({ videoId }: { videoId: number }): JSX.Element {
  const q = useFrames(videoId);
  if (q.isLoading) {
    return (
      <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))' }}>
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="aspect-video w-full" />
        ))}
      </div>
    );
  }
  if (q.isError) return <ErrorBanner message={(q.error as Error).message} />;
  const frames = q.data ?? [];
  if (frames.length === 0) return <EmptyHint message="No frame samples extracted yet." />;
  return (
    <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))' }}>
      {frames.map((f) => (
        <figure
          key={f.id}
          className="group relative overflow-hidden rounded-md border border-bg-3 bg-bg-2"
          style={{ aspectRatio: '16 / 9' }}
          title={f.description ?? ''}
        >
          <PosterFallback title={f.storage_key} videoId={f.id} />
          <figcaption className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 to-transparent p-2 text-[11px] text-text-0">
            <p className="font-mono text-text-2">{humanizeDuration(f.timestamp_seconds)}</p>
            {f.description && (
              <p className="mt-0.5 line-clamp-2 opacity-0 transition-opacity group-hover:opacity-100">
                {f.description}
              </p>
            )}
          </figcaption>
        </figure>
      ))}
    </div>
  );
}

function ErrorBanner({ message }: { message: string }): JSX.Element {
  return (
    <div role="alert" className="rounded-md border border-accent/40 bg-accent/10 p-4 text-sm text-accent">
      {message}
    </div>
  );
}

function EmptyHint({ message }: { message: string }): JSX.Element {
  return (
    <div className="rounded-md border border-dashed border-bg-3 bg-bg-1 p-8 text-center text-sm text-text-2">
      {message}
    </div>
  );
}
