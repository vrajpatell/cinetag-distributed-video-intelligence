import Link from 'next/link';
import type { VideoSummary } from '@/lib/types';
import { formatDuration } from '@/lib/format';
import { gradientForId } from '@/lib/demo-data';
import JobStatusBadge from './JobStatusBadge';

export default function VideoCard({
  video,
  variant = 'default',
}: {
  video: VideoSummary;
  variant?: 'default' | 'compact' | 'wide';
}) {
  const grad = video.thumbnailGradient || gradientForId(video.id);
  const tags = (video.tags || []).slice(0, 3);
  const widthClass =
    variant === 'compact' ? 'w-[220px]' : variant === 'wide' ? 'w-[340px]' : 'w-[280px]';

  return (
    <Link
      href={`/videos/${video.id}`}
      className={`group relative block ${widthClass} shrink-0 overflow-hidden rounded-xl border border-cinetag-border/70 bg-cinetag-panel/80 transition-all duration-300 hover:-translate-y-0.5 hover:border-cinetag-red/40 hover:shadow-cardHover`}
    >
      <div className={`relative aspect-video w-full ${grad}`}>
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/0 to-black/30" />
        <div className="absolute left-2.5 top-2.5 flex items-center gap-1.5">
          {video.processingStage ? (
            <JobStatusBadge stage={video.processingStage} compact />
          ) : video.status ? (
            <JobStatusBadge status={video.status} compact />
          ) : null}
        </div>
        <div className="absolute right-2.5 top-2.5">
          {video.confidence != null ? (
            <span className="chip-neutral !text-[10px]">
              <span className="text-white/50">conf</span>
              <span className="font-mono">{video.confidence.toFixed(2)}</span>
            </span>
          ) : null}
        </div>
        {video.duration_seconds != null ? (
          <div className="absolute bottom-2.5 right-2.5 rounded bg-black/65 px-1.5 py-0.5 font-mono text-[10px] text-white/90">
            {formatDuration(video.duration_seconds)}
          </div>
        ) : null}
        <div className="absolute inset-x-0 bottom-0 hidden h-12 bg-gradient-to-t from-black/80 to-transparent group-hover:block" />
        <div className="absolute inset-0 grid place-items-center opacity-0 transition-opacity group-hover:opacity-100">
          <div className="grid h-12 w-12 place-items-center rounded-full bg-cinetag-red/95 ring-2 ring-white/20 shadow-glow">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="white" aria-hidden>
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>
        </div>
      </div>
      <div className="p-3.5">
        <div className="flex items-start justify-between gap-2">
          <h3 className="line-clamp-1 text-[13.5px] font-semibold text-white">{video.title}</h3>
          {video.isDemo ? <span className="chip-neutral !text-[9.5px] !px-1.5 !py-0.5">demo</span> : null}
        </div>
        {video.description ? (
          <p className="mt-1 line-clamp-2 text-[11.5px] text-white/55">{video.description}</p>
        ) : null}
        <div className="mt-2.5 flex flex-wrap gap-1">
          {tags.map((t) => (
            <span key={`${t.value}-${t.type}`} className="chip-neutral !text-[10px] !px-1.5 !py-0.5">
              {t.value}
            </span>
          ))}
          {(video.tags?.length ?? 0) > tags.length ? (
            <span className="chip-neutral !text-[10px] !px-1.5 !py-0.5 text-white/55">
              +{(video.tags?.length ?? 0) - tags.length}
            </span>
          ) : null}
        </div>
        {video.recommendationReason ? (
          <div className="mt-2.5 line-clamp-1 text-[10.5px] text-cinetag-redGlow/80">
            {video.recommendationReason}
          </div>
        ) : null}
      </div>
    </Link>
  );
}
