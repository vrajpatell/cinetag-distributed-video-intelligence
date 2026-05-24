'use client';

import Link from 'next/link';
import type { VideoSummary } from '@/lib/types';
import { gradientForId } from '@/lib/demo-data';
import VideoPreviewMedia from '@/components/VideoPreviewMedia';
import JobStatusBadge from '@/components/JobStatusBadge';

export default function FeaturedPreviewCard({ video }: { video: VideoSummary }) {
  const tags = (video.tags || []).slice(0, 5);
  const grad = video.thumbnailGradient || gradientForId(video.id);

  return (
    <div className="panel-strong noise relative overflow-hidden p-5">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cinetag-redGlow/60 to-transparent" />
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-white/50">Featured asset</div>
          <Link href={`/videos/${video.id}`} className="mt-1 block text-base font-semibold text-white hover:text-cinetag-redGlow">
            {video.title}
          </Link>
          <div className="text-xs text-white/55">
            {video.duration_seconds != null ? `${Math.round(video.duration_seconds)}s` : '—'}
            {video.codec ? ` · ${video.codec}` : ''}
            {video.width && video.height ? ` · ${video.width}×${video.height}` : ''}
          </div>
        </div>
        {video.status || video.processingStage ? (
          <JobStatusBadge status={video.status} stage={video.processingStage} compact />
        ) : null}
      </div>

      <Link href={`/videos/${video.id}`} className="relative mt-4 block overflow-hidden rounded-lg">
        <VideoPreviewMedia
          videoId={video.id}
          title={video.title}
          posterUrl={video.poster_url}
          previewUrl={video.preview_url}
          thumbnailUrls={video.thumbnail_urls}
          thumbnailGradient={grad}
          durationSeconds={video.duration_seconds}
          isDemo={video.isDemo}
          showMuteToggle
        />
      </Link>

      {tags.length ? (
        <div className="mt-4">
          <div className="mb-2 text-[11px] uppercase tracking-wider text-white/50">AI tags</div>
          <div className="flex flex-wrap gap-1.5">
            {tags.map((t) => (
              <span key={`${t.type}-${t.value}`} className="chip-neutral">
                {t.value}
                {t.confidence != null ? (
                  <>
                    <span className="text-white/40">·</span>
                    <span className="font-mono text-white/60">{t.confidence.toFixed(2)}</span>
                  </>
                ) : null}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {video.recommendationReason ? (
        <div className="mt-4 panel-muted px-3 py-2.5 text-[11px] text-white/70">
          <span className="text-white/50">Recommend reason:</span> {video.recommendationReason}
        </div>
      ) : null}
    </div>
  );
}
