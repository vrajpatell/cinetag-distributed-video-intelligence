import HeroBanner from '@/components/HeroBanner';
import MetricStrip from '@/components/MetricStrip';
import VideoRail from '@/components/VideoRail';
import RecommendationRail from '@/components/RecommendationRail';
import PipelineFlow from '@/components/PipelineFlow';
import ArchitecturePanel from '@/components/ArchitecturePanel';
import { safeFetch } from '@/lib/api';
import { DEMO_METRICS, DEMO_VIDEOS } from '@/lib/demo-data';
import type { VideoSummary } from '@/lib/types';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

function buildMetrics(real: VideoSummary[]): typeof DEMO_METRICS {
  if (!real || real.length === 0) return DEMO_METRICS;
  const total = real.length;
  const completed = real.filter((v) => /completed|published|review_ready/.test(String(v.status))).length;
  return [
    { label: 'Videos Processed', value: String(total), trend: `+${total} ingested`, accent: 'red' },
    {
      label: 'Jobs Completed (24h)',
      value: String(completed),
      trend: `${total ? Math.round((completed / total) * 100) : 0}% success`,
      accent: 'emerald',
    },
    { label: 'AI Tags Generated', value: '—', trend: 'live', accent: 'violet' },
    { label: 'Searchable Assets', value: String(completed), trend: 'indexed', accent: 'sky' },
    { label: 'Avg Processing Latency', value: '—', trend: 'p50 / p95', accent: 'amber' },
    { label: 'Review Completion Rate', value: '—', trend: 'live', accent: 'rose' },
  ];
}

export default async function Home() {
  const real = await safeFetch<VideoSummary[]>('/api/videos', []);
  const usingDemo = !Array.isArray(real) || real.length === 0;
  const videos: VideoSummary[] = usingDemo ? DEMO_VIDEOS : real;

  const recently = [...videos].sort((a, b) =>
    String(b.created_at || '').localeCompare(String(a.created_at || ''))
  );
  const processing = videos.filter((v) =>
    ['processing', 'running', 'queued'].includes(String(v.status)) ||
    ['llm_tagging', 'transcription', 'frame_sampling', 'metadata_extraction', 'embedding'].includes(
      String(v.processingStage)
    )
  );
  const aiTagged = videos.filter((v) => (v.tags?.length ?? 0) >= 3);
  const needsReview = videos.filter((v) =>
    ['review_ready'].includes(String(v.status)) || ['review_ready'].includes(String(v.processingStage))
  );
  const ready = videos.filter((v) =>
    ['published', 'completed'].includes(String(v.status)) || ['completed'].includes(String(v.processingStage))
  );
  const trending = [...videos].sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0));

  const metrics = buildMetrics(real || []);

  return (
    <div className="space-y-12 pb-12">
      <HeroBanner />

      <MetricStrip metrics={metrics} />

      {usingDemo ? (
        <div className="mx-auto max-w-[1400px] px-5">
          <div className="rounded-md border border-cinetag-border/70 bg-cinetag-panelMuted/60 px-3 py-2 text-[12px] text-white/60">
            Showing demo content because no videos have been ingested yet.{' '}
            <a href="/upload" className="text-cinetag-redGlow hover:underline">
              Upload your first asset
            </a>{' '}
            to populate the rails with real data.
          </div>
        </div>
      ) : null}

      <VideoRail title="Recently uploaded" subtitle="Last assets through the ingestion pipeline" videos={recently.slice(0, 12)} />
      <VideoRail title="Processing now" subtitle="Workers are actively extracting metadata, frames, and tags" videos={processing.length ? processing : videos.slice(0, 6)} accent="sky" />
      <VideoRail title="AI-tagged content" subtitle="LLM-generated tags ready to power search and recommendations" videos={aiTagged.length ? aiTagged : videos} accent="violet" />
      <VideoRail title="Needs review" subtitle="Human-in-the-loop QA queue" videos={needsReview.length ? needsReview : videos.slice(0, 4)} accent="amber" />
      <VideoRail title="Recommendation-ready assets" subtitle="Indexed for semantic discovery and related-content rails" videos={ready.length ? ready : videos.slice(0, 8)} accent="emerald" />

      <RecommendationRail
        title='Because you tagged "fast-paced urban thrillers"'
        reason="Top decile overlap with action + tension + night-scene cluster"
        videos={trending.slice(0, 8)}
      />

      <VideoRail title="Trending genres &amp; themes" subtitle="What's bubbling up across the catalog" videos={trending} />

      <PipelineFlow />

      <ArchitecturePanel />

      <CtaSplit />
    </div>
  );
}

function CtaSplit() {
  return (
    <section className="mx-auto max-w-[1400px] px-5">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="panel-strong relative overflow-hidden p-6">
          <div className="absolute -top-12 -right-10 h-40 w-40 rounded-full bg-cinetag-red/20 blur-2xl" />
          <div className="text-[11px] uppercase tracking-wider text-white/55">Ingest</div>
          <h3 className="mt-1 text-xl font-bold tracking-tight">Bring your own video</h3>
          <p className="mt-1 text-sm text-white/60">
            CineTag uses signed direct-to-GCS uploads so the API never proxies large files. Track progress
            live, then watch the worker pipeline take over.
          </p>
          <a href="/upload" className="btn-primary mt-4">Open uploader</a>
        </div>
        <div className="panel-strong relative overflow-hidden p-6">
          <div className="absolute -bottom-12 -left-10 h-40 w-40 rounded-full bg-violet-500/20 blur-2xl" />
          <div className="text-[11px] uppercase tracking-wider text-white/55">Discover</div>
          <h3 className="mt-1 text-xl font-bold tracking-tight">Search your library semantically</h3>
          <p className="mt-1 text-sm text-white/60">
            Ask in natural language — "tense night scenes with cars", "calm wildlife reels". CineTag finds
            it via tag &amp; embedding similarity, with explainable matches.
          </p>
          <a href="/search" className="btn-secondary mt-4">Try semantic search</a>
        </div>
      </div>
    </section>
  );
}
