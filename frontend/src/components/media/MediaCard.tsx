import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Play, Plus, ThumbsDown, ThumbsUp } from 'lucide-react';
import { cn } from '@/lib/cn';
import { humanizeDuration, truncate } from '@/lib/format';
import type { VideoAsset } from '@/lib/zodSchemas';

export interface MediaCardProps {
  video: VideoAsset;
  score?: number;
  explanation?: string;
  className?: string;
  size?: 'sm' | 'md';
  onPlay?: () => void;
  onAdd?: () => void;
  onApprove?: () => void;
  onReject?: () => void;
}

export function MediaCard({
  video,
  score,
  explanation,
  className,
  size = 'md',
  onPlay,
  onAdd,
  onApprove,
  onReject,
}: MediaCardProps): JSX.Element {
  const navigate = useNavigate();
  const dim = size === 'sm' ? 'h-[120px] w-[213px]' : 'h-[135px] w-[240px]';
  const handleNav = () => navigate(`/videos/${video.id}`);

  return (
    <motion.article
      layout
      whileHover={{ scale: 1.08, y: -4, zIndex: 20 }}
      whileFocus={{ scale: 1.08, y: -4, zIndex: 20 }}
      transition={{ type: 'spring', stiffness: 320, damping: 26 }}
      tabIndex={0}
      role="link"
      aria-label={`Open ${video.title ?? video.original_filename}`}
      onKeyDown={(e) => {
        if (e.key === 'Enter') handleNav();
      }}
      onClick={handleNav}
      className={cn(
        'group relative shrink-0 cursor-pointer overflow-hidden rounded-md bg-bg-2 shadow-card outline-none',
        'focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg-0',
        dim,
        className,
      )}
    >
      <PosterFallback title={video.title ?? video.original_filename} videoId={video.id} />

      {typeof score === 'number' && (
        <div className="absolute inset-x-0 bottom-0 h-1 bg-bg-3">
          <div
            className="h-full bg-accent"
            style={{ width: `${Math.min(100, Math.max(0, score * 100))}%` }}
          />
        </div>
      )}

      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/85 via-black/30 to-transparent opacity-100 transition-opacity duration-200 group-hover:opacity-100" />

      <div className="absolute inset-x-0 bottom-0 p-3">
        <h3 className="line-clamp-1 font-display text-sm font-semibold tracking-tight text-text-0">
          {video.title ?? video.original_filename}
        </h3>
        <p className="mt-0.5 line-clamp-1 text-[11px] text-text-1">
          {humanizeDuration(video.duration_seconds ?? null)}
          {video.codec ? ` · ${video.codec}` : ''}
          {video.width && video.height ? ` · ${video.height}p` : ''}
        </p>
      </div>

      <div
        className="pointer-events-none absolute inset-x-0 bottom-0 translate-y-3 bg-gradient-to-t from-bg-1 via-bg-1/95 to-transparent p-3 opacity-0 transition-all duration-200 group-hover:pointer-events-auto group-hover:translate-y-0 group-hover:opacity-100"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="line-clamp-1 font-display text-sm font-semibold tracking-tight text-text-0">
          {video.title ?? video.original_filename}
        </h3>
        {explanation && (
          <p className="mt-1 line-clamp-2 text-[11px] text-text-1">{truncate(explanation, 120)}</p>
        )}
        <div className="mt-2 flex items-center gap-1.5">
          <QuickAction label="Play" onClick={onPlay ?? handleNav}>
            <Play className="h-3.5 w-3.5" aria-hidden />
          </QuickAction>
          <QuickAction label="Add to list" onClick={onAdd}>
            <Plus className="h-3.5 w-3.5" aria-hidden />
          </QuickAction>
          <QuickAction label="Approve" onClick={onApprove}>
            <ThumbsUp className="h-3.5 w-3.5" aria-hidden />
          </QuickAction>
          <QuickAction label="Reject" onClick={onReject}>
            <ThumbsDown className="h-3.5 w-3.5" aria-hidden />
          </QuickAction>
        </div>
      </div>
    </motion.article>
  );
}

function QuickAction({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick?: () => void;
  children: React.ReactNode;
}): JSX.Element {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      disabled={!onClick}
      className={cn(
        'inline-flex h-7 w-7 items-center justify-center rounded-full border border-bg-3 bg-black/60 text-text-0 transition-colors',
        onClick ? 'hover:bg-white hover:text-black' : 'cursor-not-allowed opacity-40',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
      )}
    >
      {children}
    </button>
  );
}

const POSTER_GRADIENTS = [
  'linear-gradient(135deg, #831010 0%, #1a1a1f 100%)',
  'linear-gradient(135deg, #0b0b0f 0%, #2a2a31 100%)',
  'linear-gradient(135deg, #2a2a31 0%, #831010 100%)',
  'linear-gradient(135deg, #1a1a1f 0%, #e50914 120%)',
  'linear-gradient(135deg, #46d369 -50%, #0b0b0f 100%)',
  'linear-gradient(135deg, #f5a623 -60%, #1a1a1f 100%)',
];

export function PosterFallback({ title, videoId }: { title: string; videoId: number }): JSX.Element {
  const idx = Math.abs(hashCode(title + videoId)) % POSTER_GRADIENTS.length;
  return (
    <div
      aria-hidden
      className="absolute inset-0"
      style={{ backgroundImage: POSTER_GRADIENTS[idx] }}
    >
      <div className="flex h-full items-end p-3">
        <span className="font-display text-3xl font-black tracking-tightest text-white/15">
          {title.slice(0, 1).toUpperCase()}
        </span>
      </div>
    </div>
  );
}

function hashCode(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i += 1) {
    h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  }
  return h;
}
