'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { searchVideos } from '@/lib/api';
import { DEMO_SEARCH_RESULTS, SEARCH_EXAMPLES, gradientForId } from '@/lib/demo-data';
import type { SearchResult } from '@/lib/types';
import { formatDuration } from '@/lib/format';

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
  const [results, setResults] = useState<SearchResult[]>([]);
  const [usedDemo, setUsedDemo] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);

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

  const submit = async (q: string) => {
    setError(null);
    setLoading(true);
    setResults([]);
    setUsedDemo(false);
    try {
      const r = await searchVideos({ query: q });
      if (Array.isArray(r) && r.length > 0) {
        setResults(r);
      } else {
        setResults(DEMO_SEARCH_RESULTS);
        setUsedDemo(true);
      }
    } catch (err) {
      setResults(DEMO_SEARCH_RESULTS);
      setUsedDemo(true);
      setError(err instanceof Error ? err.message : 'Search failed; showing demo results.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="panel-strong relative overflow-hidden p-5 md:p-6">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cinetag-redGlow/60 to-transparent" />
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!query.trim()) return;
            submit(query.trim());
          }}
          className="flex flex-col gap-3 md:flex-row md:items-center"
        >
          <div className="relative flex-1">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-white/45">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
                <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
                <path d="m20 20-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </span>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder='Try: "find suspenseful night scenes with cars"'
              className="w-full rounded-lg border border-cinetag-border bg-cinetag-panelMuted/80 px-10 py-3 text-sm text-white placeholder:text-white/40 outline-none transition focus:border-cinetag-red/60 focus:ring-2 focus:ring-cinetag-red/20"
            />
          </div>
          <button
            type="submit"
            disabled={!query.trim() || loading}
            className="btn-primary md:w-auto"
          >
            {loading ? 'Searching…' : 'Semantic search'}
          </button>
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
              className="chip-neutral hover:bg-white/10 cursor-pointer"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

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

          {filteredResults.map((r) => (
            <ResultRow key={String(r.video_id)} r={r} />
          ))}
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
        <select
          value={filters.genre}
          onChange={(e) => onChange({ ...filters, genre: e.target.value })}
          className="select-style"
        >
          <option value="">Any</option>
          {['Action', 'Adventure', 'Comedy', 'Crime', 'Documentary', 'Drama', 'Nature', 'Sci-Fi', 'Sports', 'Thriller'].map(
            (g) => (
              <option key={g} value={g}>
                {g}
              </option>
            )
          )}
        </select>
      </Field>
      <Field label="Mood">
        <select
          value={filters.mood}
          onChange={(e) => onChange({ ...filters, mood: e.target.value })}
          className="select-style"
        >
          <option value="">Any</option>
          {['Tense', 'Suspenseful', 'Reflective', 'Inspirational', 'Humorous', 'Serene', 'Ominous', 'Tranquil'].map(
            (m) => (
              <option key={m} value={m}>
                {m}
              </option>
            )
          )}
        </select>
      </Field>
      <Field label="Status">
        <select
          value={filters.status}
          onChange={(e) => onChange({ ...filters, status: e.target.value })}
          className="select-style"
        >
          <option value="">Any</option>
          <option value="review_ready">Review ready</option>
          <option value="published">Published</option>
          <option value="processing">Processing</option>
          <option value="uploaded">Uploaded</option>
        </select>
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
      <button
        type="button"
        onClick={() => onChange(DEFAULT_FILTERS)}
        className="btn-ghost w-full !justify-center !py-1.5 !text-[12px]"
      >
        Reset filters
      </button>
      <style>{`
        .select-style {
          width: 100%;
          background: rgba(16,19,26,0.7);
          border: 1px solid rgba(255,255,255,0.08);
          color: #F5F7FA;
          border-radius: 8px;
          padding: 6px 10px;
          font-size: 12.5px;
          outline: none;
        }
        .select-style:focus { border-color: rgba(229,9,20,0.5); }
      `}</style>
    </aside>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="mb-1 text-[11px] text-white/55">{label}</div>
      {children}
    </label>
  );
}

function ResultRow({ r }: { r: SearchResult }) {
  const grad = r.thumbnailGradient || gradientForId(r.video_id);
  return (
    <Link
      href={`/videos/${r.video_id}`}
      className="panel group flex items-center gap-4 p-3 transition-colors hover:border-cinetag-red/40"
    >
      <div className={`relative h-20 w-32 shrink-0 overflow-hidden rounded-md ${grad}`}>
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-black/10" />
        {r.duration_seconds != null ? (
          <div className="absolute bottom-1.5 right-1.5 rounded bg-black/65 px-1.5 py-0.5 font-mono text-[10px] text-white/90">
            {formatDuration(r.duration_seconds)}
          </div>
        ) : null}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold text-white">{r.title || `Video #${r.video_id}`}</h3>
          <span className="chip-emerald !text-[10px]">
            <span className="font-mono">{(r.score * 100).toFixed(0)}%</span> match
          </span>
          {r.isDemo ? <span className="chip-neutral !text-[10px]">demo</span> : null}
        </div>
        {r.explanation ? (
          <p className="mt-1 line-clamp-1 text-[12px] text-white/55">{r.explanation}</p>
        ) : null}
        <div className="mt-2 flex flex-wrap gap-1">
          {(r.matched_tags || []).slice(0, 5).map((t, i) => (
            <span key={`${t.value}-${i}`} className="chip-neutral !text-[10px]">
              {t.value}
            </span>
          ))}
        </div>
      </div>
      <div className="hidden md:flex items-center text-white/40 group-hover:text-white">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
          <path d="M9 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    </Link>
  );
}
