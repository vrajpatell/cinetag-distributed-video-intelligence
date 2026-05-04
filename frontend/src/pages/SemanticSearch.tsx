import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Search, Sparkles, X } from 'lucide-react';
import { Skeleton } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/Button';
import { RangeSlider } from '@/components/ui/RangeSlider';
import { useSemanticSearch } from '@/state/hooks/useSemanticSearch';
import { useVideos } from '@/state/hooks/useVideos';
import { MediaCard, PosterFallback } from '@/components/media/MediaCard';
import { humanizeDuration, truncate } from '@/lib/format';
import type { SearchResult, VideoAsset } from '@/lib/zodSchemas';

const TAG_TYPES = ['', 'genre', 'mood', 'object', 'person', 'scene', 'topic'];
const TAG_STATUS = ['', 'approved', 'pending_review', 'rejected'];
const SUGGESTIONS = [
  'sunlit beach with friends laughing',
  'dramatic boardroom argument',
  'aerial city night skyline',
  'kids playing in the snow',
];

export default function SearchPage(): JSX.Element {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [debounced, setDebounced] = useState('');
  const [tagType, setTagType] = useState('');
  const [status, setStatus] = useState('');
  const [duration, setDuration] = useState<[number, number]>([0, 7200]);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const handle = window.setTimeout(() => setDebounced(query), 350);
    return () => window.clearTimeout(handle);
  }, [query]);

  const filters = useMemo(
    () => ({
      tag_type: tagType || undefined,
      status: status || undefined,
      duration_min: duration[0] > 0 ? duration[0] : undefined,
      duration_max: duration[1] < 7200 ? duration[1] : undefined,
    }),
    [tagType, status, duration],
  );

  const searchQ = useSemanticSearch({ query: debounced, ...filters });
  const videosQ = useVideos();

  const videosById = useMemo(() => {
    const map = new Map<number, VideoAsset>();
    for (const v of videosQ.data ?? []) map.set(v.id, v);
    return map;
  }, [videosQ.data]);

  const showResults = debounced.trim().length > 0;

  return (
    <div className="mx-auto max-w-rail px-4 pb-16 pt-8 sm:px-6 lg:px-12">
      <header className="mx-auto max-w-3xl text-center">
        <h1 className="font-display text-4xl font-bold tracking-tightest text-text-0 sm:text-5xl">
          Semantic search
        </h1>
        <p className="mt-2 text-sm text-text-1">
          Describe what you want to find. We'll match by meaning across transcripts, scenes and tags.
        </p>

        <div className="relative mx-auto mt-6 max-w-2xl">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-text-2" aria-hidden />
          <input
            ref={inputRef}
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. sunny beach with friends"
            aria-label="Search videos by meaning"
            className="h-14 w-full rounded-full border border-bg-3 bg-bg-1 pl-12 pr-12 text-base text-text-0 placeholder:text-text-2 transition-colors focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent"
          />
          {query && (
            <button
              type="button"
              onClick={() => {
                setQuery('');
                setDebounced('');
                inputRef.current?.focus();
              }}
              aria-label="Clear search"
              className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-2 text-text-2 transition-colors hover:bg-bg-2 hover:text-text-0"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          )}
        </div>

        <div className="mx-auto mt-6 grid max-w-3xl grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <FilterSelect label="Tag type" value={tagType} options={TAG_TYPES} onChange={setTagType} />
          <FilterSelect label="Status" value={status} options={TAG_STATUS} onChange={setStatus} />
          <div className="rounded-md border border-bg-3 bg-bg-1 px-4 py-3 text-left">
            <RangeSlider
              label="Duration"
              min={0}
              max={7200}
              step={30}
              value={duration}
              onChange={setDuration}
              formatValue={(n) => humanizeDuration(n)}
            />
          </div>
        </div>
      </header>

      <section className="mt-10">
        {!showResults ? (
          <EmptySearchHint
            onPick={(s) => {
              setQuery(s);
              inputRef.current?.focus();
            }}
          />
        ) : searchQ.isLoading || searchQ.isFetching ? (
          <ResultsSkeleton />
        ) : searchQ.isError ? (
          <ErrorBanner message={(searchQ.error as Error).message} />
        ) : (searchQ.data ?? []).length === 0 ? (
          <NoResults />
        ) : (
          <ResultsGrid
            results={searchQ.data ?? []}
            videosById={videosById}
            onOpen={(id) => navigate(`/videos/${id}`)}
          />
        )}
      </section>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}): JSX.Element {
  return (
    <label className="rounded-md border border-bg-3 bg-bg-1 px-4 py-3 text-left">
      <span className="block text-xs font-medium text-text-1">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full bg-transparent text-sm text-text-0 focus:outline-none"
      >
        {options.map((opt) => (
          <option key={opt || 'any'} value={opt} className="bg-bg-1 text-text-0">
            {opt === '' ? 'Any' : opt.replaceAll('_', ' ')}
          </option>
        ))}
      </select>
    </label>
  );
}

function ResultsGrid({
  results,
  videosById,
  onOpen,
}: {
  results: SearchResult[];
  videosById: Map<number, VideoAsset>;
  onOpen: (id: number) => void;
}): JSX.Element {
  return (
    <div
      className="grid gap-4"
      style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))' }}
    >
      {results.map((r) => {
        const v = videosById.get(r.video_id);
        if (v) {
          return (
            <div key={r.video_id} className="flex flex-col gap-2">
              <MediaCard
                video={v}
                score={r.score}
                explanation={r.explanation}
                className="w-full"
              />
              <p className="line-clamp-2 text-xs text-text-1">{r.explanation}</p>
            </div>
          );
        }
        return (
          <button
            key={r.video_id}
            type="button"
            onClick={() => onOpen(r.video_id)}
            className="group relative h-[135px] w-full overflow-hidden rounded-md border border-bg-3 bg-bg-1 text-left transition-transform hover:-translate-y-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            <PosterFallback title={r.title ?? `Video #${r.video_id}`} videoId={r.video_id} />
            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 to-transparent p-3">
              <p className="line-clamp-1 text-sm font-semibold text-text-0">
                {r.title ?? `Video #${r.video_id}`}
              </p>
              <p className="line-clamp-1 text-[11px] text-text-1">{truncate(r.explanation, 64)}</p>
            </div>
            <div className="absolute inset-x-0 bottom-0 h-1 bg-bg-3">
              <div
                className="h-full bg-accent"
                style={{ width: `${Math.min(100, Math.max(0, r.score * 100))}%` }}
              />
            </div>
          </button>
        );
      })}
    </div>
  );
}

function ResultsSkeleton(): JSX.Element {
  return (
    <div
      className="grid gap-4"
      style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))' }}
    >
      {Array.from({ length: 8 }).map((_, i) => (
        <Skeleton key={i} className="h-[180px] w-full" />
      ))}
      <div className="col-span-full flex items-center gap-2 text-sm text-text-2">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Searching…
      </div>
    </div>
  );
}

function EmptySearchHint({ onPick }: { onPick: (s: string) => void }): JSX.Element {
  return (
    <div className="mx-auto max-w-2xl rounded-xl border border-dashed border-bg-3 bg-bg-1 p-8 text-center">
      <Sparkles className="mx-auto h-8 w-8 text-accent" aria-hidden />
      <p className="mt-3 font-display text-lg font-semibold text-text-0">
        Search across every video, scene and transcript
      </p>
      <p className="mt-1 text-sm text-text-1">
        Try one of these to see semantic ranking in action.
      </p>
      <ul className="mt-4 flex flex-wrap items-center justify-center gap-2">
        {SUGGESTIONS.map((s) => (
          <li key={s}>
            <Button variant="secondary" size="sm" onClick={() => onPick(s)}>
              {s}
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function NoResults(): JSX.Element {
  return (
    <div className="mx-auto max-w-xl rounded-xl border border-bg-3 bg-bg-1 p-8 text-center">
      <p className="font-display text-lg font-semibold text-text-0">No matches yet</p>
      <p className="mt-1 text-sm text-text-1">
        Try loosening filters or rephrasing your query. Embeddings work best with descriptive language.
      </p>
    </div>
  );
}

function ErrorBanner({ message }: { message: string }): JSX.Element {
  return (
    <div role="alert" className="mx-auto max-w-xl rounded-md border border-accent/40 bg-accent/10 p-4 text-sm text-accent">
      Search failed: {message}
    </div>
  );
}
