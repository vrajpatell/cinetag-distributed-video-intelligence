'use client';

import Link from 'next/link';
import type { VideoSummary } from '@/lib/types';
import { gradientForId } from '@/lib/demo-data';
import VideoPreviewMedia from '@/components/VideoPreviewMedia';
import JobStatusBadge from '@/components/JobStatusBadge';
import { formatBitsPerSecond, formatBytes, formatDuration } from '@/lib/format';

export default function VideoDetailHero({
  video,
  isDemo,
}: {
  video: VideoSummary;
  isDemo?: boolean;
}) {
  const grad = video.thumbnailGradient || gradientForId(video.id);

  return (
    <div className="relative aspect-[21/9] w-full overflow-hidden">
      <VideoPreviewMedia
        videoId={video.id}
        title={video.title}
        posterUrl={video.poster_url}
        previewUrl={video.preview_url}
        thumbnailUrls={video.thumbnail_urls}
        thumbnailGradient={grad}
        durationSeconds={video.duration_seconds}
        isDemo={isDemo ?? video.isDemo}
        showMuteToggle
        className="!aspect-[21/9] h-full"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/20 to-black/30 pointer-events-none" />
      <div className="absolute right-4 top-4 z-10 flex flex-wrap gap-1.5 pointer-events-none">
        {video.status ? <JobStatusBadge status={String(video.status)} /> : null}
        {video.processingStage ? <JobStatusBadge stage={String(video.processingStage)} /> : null}
        {isDemo ? <span className="chip-neutral">demo</span> : null}
      </div>
      <div className="absolute inset-x-6 bottom-6 z-10 flex flex-col gap-3 md:flex-row md:items-end md:justify-between pointer-events-none">
        <div className="max-w-3xl">
          <h1 className="text-balance text-3xl font-extrabold tracking-tight md:text-5xl">
            {video.title || `Video #${video.id}`}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-[12px] text-white/70">
            {video.duration_seconds != null ? <span>{formatDuration(video.duration_seconds)}</span> : null}
            {video.width && video.height ? <span>{video.width}×{video.height}</span> : null}
            {video.codec ? <span className="font-mono">{video.codec}</span> : null}
            {video.bitrate ? <span>{formatBitsPerSecond(video.bitrate / 8)}</span> : null}
            {video.file_size_bytes ? <span>{formatBytes(video.file_size_bytes)}</span> : null}
          </div>
        </div>
        <div className="flex flex-wrap gap-2 pointer-events-auto">
          <Link href="/jobs" className="btn-secondary">View pipeline jobs</Link>
          <Link href="/search" className="btn-primary">Find similar</Link>
        </div>
      </div>
    </div>
  );
}
