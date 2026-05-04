import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { Billboard } from '@/components/media/Billboard';
import { Carousel } from '@/components/media/Carousel';
import { MediaCard } from '@/components/media/MediaCard';
import { Skeleton } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/Button';
import { useVideos } from '@/state/hooks/useVideos';
import { useJobs } from '@/state/hooks/useJobs';
import { useTranscript } from '@/state/hooks/useVideoDetails';
import type { ProcessingJob, VideoAsset } from '@/lib/zodSchemas';

export default function BrowsePage(): JSX.Element {
  const videosQ = useVideos();
  const jobsQ = useJobs();

  const featured = useMemo<VideoAsset | null>(() => {
    const list = videosQ.data ?? [];
    if (list.length === 0) return null;
    return [...list].sort((a, b) => (a.created_at < b.created_at ? 1 : -1))[0];
  }, [videosQ.data]);

  const featuredTranscriptQ = useTranscript(featured?.id);

  const overview = featuredTranscriptQ.data?.text?.slice(0, 240) ?? null;

  if (videosQ.isLoading) return <BrowseSkeleton />;

  if (videosQ.isError) {
    return (
      <ErrorState
        title="Could not load videos"
        message={(videosQ.error as Error)?.message ?? 'Unknown error'}
      />
    );
  }

  if (!featured) return <EmptyBrowse />;

  return (
    <div className="-mt-16 pb-16">
      <Billboard video={featured} overview={overview} />

      <div className="mx-auto max-w-rail">
        <ProcessingRow jobs={jobsQ.data ?? []} videos={videosQ.data ?? []} />
        <RecentlyTaggedRow videos={videosQ.data ?? []} />
        <AwaitingReviewRow videos={videosQ.data ?? []} />
        <AllVideosRow videos={videosQ.data ?? []} />
      </div>
    </div>
  );
}

function ProcessingRow({
  jobs,
  videos,
}: {
  jobs: ProcessingJob[];
  videos: VideoAsset[];
}): JSX.Element {
  const active = jobs.filter((j) => j.status === 'queued' || j.status === 'running');
  const videosById = new Map(videos.map((v) => [v.id, v]));
  return (
    <Carousel
      title="Continue processing"
      description="Jobs currently running or queued"
      cta={
        <Link to="/jobs">
          <Button variant="ghost" size="sm" iconRight={<ChevronRight className="h-4 w-4" aria-hidden />}>
            All jobs
          </Button>
        </Link>
      }
      emptyMessage={
        active.length === 0 ? 'No active jobs. Nothing to babysit right now.' : undefined
      }
    >
      {active.slice(0, 12).map((job) => {
        const v = videosById.get(job.video_id);
        if (!v) return null;
        return (
          <MediaCard
            key={`processing-${job.id}`}
            video={v}
            explanation={job.current_stage ? `Stage: ${job.current_stage}` : `Status: ${job.status}`}
            className="snap-start"
          />
        );
      })}
    </Carousel>
  );
}

function RecentlyTaggedRow({ videos }: { videos: VideoAsset[] }): JSX.Element {
  const recent = [...videos]
    .filter((v) => v.status === 'tagged' || v.status === 'ready' || v.status === 'completed')
    .sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1))
    .slice(0, 12);
  return (
    <Carousel
      title="Recently tagged"
      description="Latest videos with fresh AI-generated tags"
      emptyMessage={recent.length === 0 ? 'No tagged videos yet.' : undefined}
    >
      {recent.map((v) => (
        <MediaCard key={`recent-${v.id}`} video={v} className="snap-start" />
      ))}
    </Carousel>
  );
}

function AwaitingReviewRow({ videos }: { videos: VideoAsset[] }): JSX.Element {
  const candidates = videos.slice(0, 12);
  return (
    <Carousel
      title="Awaiting review"
      description="Tags pending human approval"
      cta={
        <Link to="/review">
          <Button variant="ghost" size="sm" iconRight={<ChevronRight className="h-4 w-4" aria-hidden />}>
            Open queue
          </Button>
        </Link>
      }
      emptyMessage={candidates.length === 0 ? 'Nothing awaiting review.' : undefined}
    >
      {candidates.map((v) => (
        <MediaCard key={`review-${v.id}`} video={v} className="snap-start" />
      ))}
    </Carousel>
  );
}

function AllVideosRow({ videos }: { videos: VideoAsset[] }): JSX.Element {
  const list = [...videos].sort((a, b) => (a.created_at < b.created_at ? 1 : -1)).slice(0, 24);
  return (
    <Carousel
      title="All videos"
      description="Most recently uploaded first"
      emptyMessage={list.length === 0 ? 'No videos uploaded yet.' : undefined}
    >
      {list.map((v) => (
        <MediaCard key={`all-${v.id}`} video={v} className="snap-start" />
      ))}
    </Carousel>
  );
}

function BrowseSkeleton(): JSX.Element {
  return (
    <div className="-mt-16">
      <div className="relative min-h-[520px] overflow-hidden" style={{ height: '80vh' }}>
        <Skeleton className="absolute inset-0 rounded-none" />
      </div>
      <div className="mx-auto max-w-rail">
        {Array.from({ length: 3 }).map((_, i) => (
          <section key={i} className="px-4 py-6 sm:px-6 lg:px-12">
            <Skeleton className="mb-3 h-6 w-48" />
            <div className="flex gap-3 overflow-hidden">
              {Array.from({ length: 6 }).map((__, j) => (
                <Skeleton key={j} className="h-[135px] w-[240px] shrink-0" />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

function EmptyBrowse(): JSX.Element {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-2xl flex-col items-center justify-center gap-4 px-6 text-center">
      <p className="font-display text-3xl font-bold tracking-tightest text-text-0">No videos yet</p>
      <p className="text-sm text-text-1">
        Upload your first asset to start the analysis pipeline. Frames, scenes, transcripts and tags will appear here.
      </p>
      <Link to="/upload">
        <Button size="lg" variant="primary">
          Upload a video
        </Button>
      </Link>
    </div>
  );
}

function ErrorState({ title, message }: { title: string; message: string }): JSX.Element {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-2xl flex-col items-center justify-center gap-3 px-6 text-center">
      <p className="font-display text-3xl font-bold tracking-tightest text-text-0">{title}</p>
      <p className="text-sm text-text-1">{message}</p>
    </div>
  );
}
