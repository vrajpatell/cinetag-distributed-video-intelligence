'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { Search, ChevronRight } from 'lucide-react';
import { useSemanticSearch } from '@/lib/hooks/use-search';
import { SEARCH_EXAMPLES, gradientForId } from '@/lib/demo-data';
import type { SearchResult } from '@/lib/types';
import { FadeIn, StaggerChildren, StaggerItem } from '@/components/motion/Motion';
import VideoPreviewMedia from '@/components/VideoPreviewMedia';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

type Filters = {
  genre: string;
  mood: string;
  status: string;
  minConfidence: number;
};

const DEFAULT_FILTERS: Filters = {
  genre: '',
  mood: '',
  status: '',
  minConfidence: 0,
};

export default function SearchExperience({ initialQuery = '' }: { initialQuery?: string }) {
  const [query, setQuery] = useState(initialQuery);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const searchMutation = useSemanticSearch();

  const results = searchMutation.data?.results ?? [];
  const usedDemo = searchMutation.data?.usedDemo ?? false;
  const error = searchMutation.data?.error ?? null;
  const loading = searchMutation.isPending;

  const filteredResults = useMemo(() => {
    return results.filter((r) => {
      if (
        filters.genre &&
        !r.genres?.some((g) => g.toLowerCase() === filters.genre.toLowerCase())
      ) {
        return false;
      }
      if (
        filters.mood &&
        !r.moods?.some((m) => m.toLowerCase() === filters.mood.toLowerCase())
      ) {
        return false;
      }
      if (filters.status && String(r.status ?? '').toLowerCase() !== filters.status.toLowerCase()) {
        return false;
      }
      if (filters.minConfidence > 0 && r.score < filters.minConfidence) {
        return false;
      }
      return true;
    });
  }, [results, filters]);

  const submit = (q: string) => {
    if (!q.trim()) return;
    searchMutation.mutate(q.trim());
  };

  return (
    <div className="space-y-6">
      <FadeIn>
        <div className="panel-strong relative overflow-hidden p-5 md:p-6">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cinetag-redGlow/60 to-transparent" />
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit(query.trim());
            }}
            className="flex flex-col gap-3 md:flex-row md:items-center"
          >
            <div className="relative flex-1">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-white/45"
                aria-hidden
              />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder='Try: "find suspenseful night scenes with cars"'
                className="!h-11 !pl-10 !text-sm"
              />
            </div>
            <Button type="submit" disabled={!query.trim() || loading} className="md:w-auto">
              {loading ? 'Searching…' : 'Semantic search'}
            </Button>
          </form>

          <div className="mt-3 flex flex-wrap gap-1.5">
            <span className="text-[11px] text-white/50 mr-1">Try:</span>
            {SEARCH_EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => {
                  setQuery(ex);
                  submit(ex);
                }}
                className="chip-neutral hover:bg-white/10 cursor-pointer transition-colors"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      </FadeIn>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[260px,1fr]">
        <FilterPanel filters={filters} onChange={setFilters} />
        <div className="space-y-3">
          {error ? (
            <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-[12.5px] text-amber-200">
              {error}
            </div>
          ) : null}
          {usedDemo ? (
            <div className="rounded-md border border-cinetag-border/70 bg-cinetag-panelMuted/60 px-3 py-2 text-[12px] text-white/65">
              Showing demo search results — no live index yet. Connect a backend with embeddings to power
              real semantic discovery.
            </div>
          ) : null}
          {!loading && filteredResults.length === 0 ? (
            <div className="panel p-8 text-center text-sm text-white/55">
              {results.length === 0
                ? 'Run a search to discover content semantically.'
                : 'No results match your filters. Try widening them.'}
            </div>
          ) : null}

          <StaggerChildren className="space-y-3">
            {filteredResults.map((r) => (
              <StaggerItem key={String(r.video_id)}>
                <ResultRow r={r} />
              </StaggerItem>
            ))}
          </StaggerChildren>
        </div>
      </div>
    </div>
  );
}

function FilterPanel({
  filters,
  onChange,
}: {
  filters: Filters;
  onChange: (f: Filters) => void;
}) {
  return (
    <aside className="panel space-y-4 p-4">
      <div className="text-[11px] uppercase tracking-wider text-white/50">Filters</div>
      <Field label="Genre">
        <Select
          value={filters.genre || '__any__'}
          onValueChange={(v) => onChange({ ...filters, genre: v === '__any__' ? '' : v })}
        >
          <SelectTrigger className="!text-[12.5px]">
            <SelectValue placeholder="Any" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__any__">Any</SelectItem>
            {['Action', 'Adventure', 'Comedy', 'Crime', 'Documentary', 'Drama', 'Nature', 'Sci-Fi', 'Sports', 'Thriller'].map(
              (g) => (
                <SelectItem key={g} value={g}>
                  {g}
                </SelectItem>
              ),
            )}
          </SelectContent>
        </Select>
      </Field>
      <Field label="Mood">
        <Select
          value={filters.mood || '__any__'}
          onValueChange={(v) => onChange({ ...filters, mood: v === '__any__' ? '' : v })}
        >
          <SelectTrigger className="!text-[12.5px]">
            <SelectValue placeholder="Any" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__any__">Any</SelectItem>
            {['Tense', 'Suspenseful', 'Reflective', 'Inspirational', 'Humorous', 'Serene', 'Ominous', 'Tranquil'].map(
              (m) => (
                <SelectItem key={m} value={m}>
                  {m}
                </SelectItem>
              ),
            )}
          </SelectContent>
        </Select>
      </Field>
      <Field label="Status">
        <Select
          value={filters.status || '__any__'}
          onValueChange={(v) => onChange({ ...filters, status: v === '__any__' ? '' : v })}
        >
          <SelectTrigger className="!text-[12.5px]">
            <SelectValue placeholder="Any" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__any__">Any</SelectItem>
            <SelectItem value="review_ready">Review ready</SelectItem>
            <SelectItem value="published">Published</SelectItem>
            <SelectItem value="processing">Processing</SelectItem>
            <SelectItem value="uploaded">Uploaded</SelectItem>
          </SelectContent>
        </Select>
      </Field>
      <Field label={`Min confidence: ${filters.minConfidence.toFixed(2)}`}>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={filters.minConfidence}
          onChange={(e) => onChange({ ...filters, minConfidence: parseFloat(e.target.value) })}
          className="w-full accent-cinetag-red"
        />
      </Field>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => onChange(DEFAULT_FILTERS)}
        className="w-full !text-[12px]"
      >
        Reset filters
      </Button>
    </aside>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="block space-y-1">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

function ResultRow({ r }: { r: SearchResult }) {
  const grad = r.thumbnailGradient || gradientForId(r.video_id);
  return (
    <Link
      href={`/videos/${r.video_id}`}
      className="panel group flex items-center gap-4 p-3 transition-all duration-200 hover:border-cinetag-red/40 hover:-translate-y-0.5"
    >
      <div className="relative h-20 w-32 shrink-0 overflow-hidden rounded-md">
        <VideoPreviewMedia
          videoId={r.video_id}
          title={r.title}
          posterUrl={r.poster_url}
          previewUrl={r.preview_url}
          thumbnailUrls={r.thumbnail_urls}
          thumbnailGradient={grad}
          durationSeconds={r.duration_seconds}
          isDemo={r.isDemo}
          className="!aspect-auto h-full"
        />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold text-white">{r.title || `Video #${r.video_id}`}</h3>
          <Badge variant="emerald" className="!text-[10px]">
            <span className="font-mono">{(r.score * 100).toFixed(0)}%</span> match
          </Badge>
          {r.isDemo ? <Badge className="!text-[10px]">demo</Badge> : null}
        </div>
        {r.explanation ? (
          <p className="mt-1 line-clamp-1 text-[12px] text-white/55">{r.explanation}</p>
        ) : null}
        <div className="mt-2 flex flex-wrap gap-1">
          {(r.matched_tags || []).slice(0, 5).map((t, i) => (
            <Badge key={`${t.value}-${i}`} className="!text-[10px]">
              {t.value}
            </Badge>
          ))}
        </div>
      </div>
      <div className="hidden md:flex items-center text-white/40 group-hover:text-white transition-colors">
        <ChevronRight className="h-4 w-4" aria-hidden />
      </div>
    </Link>
  );
}
