'use client';

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
} from 'react';
import { Volume2, VolumeX } from 'lucide-react';
import { usePreviewPreferences } from '@/components/providers/PreviewPreferencesProvider';
import { useVideoPreviewLazy } from '@/lib/hooks/use-video-preview';
import { cn } from '@/lib/utils';

export type VideoPreviewMediaProps = {
  videoId: number | string;
  title?: string;
  posterUrl?: string | null;
  previewUrl?: string | null;
  thumbnailUrls?: string[];
  thumbnailGradient?: string;
  durationSeconds?: number | null;
  /** Demo tiles skip network preview fetches */
  isDemo?: boolean;
  className?: string;
  showMuteToggle?: boolean;
};

type PreviewPhase = 'poster' | 'loading' | 'video' | 'flipbook';

export default function VideoPreviewMedia({
  videoId,
  title,
  posterUrl,
  previewUrl: previewUrlProp,
  thumbnailUrls = [],
  thumbnailGradient,
  durationSeconds,
  isDemo = false,
  className,
  showMuteToggle = false,
}: VideoPreviewMediaProps) {
  const { autoplayMode, flipbookFallback } = usePreviewPreferences();
  const rootRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [inView, setInView] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [phase, setPhase] = useState<PreviewPhase>('poster');
  const [flipIndex, setFlipIndex] = useState(0);
  const [muted, setMuted] = useState(true);
  const [userUnmuted, setUserUnmuted] = useState(false);

  const shouldActivate =
    autoplayMode !== 'off' &&
    (autoplayMode === 'viewport' ? inView : hovered);

  const needsLazyPreview =
    shouldActivate && !isDemo && !previewUrlProp && typeof videoId === 'number';

  const lazyPreview = useVideoPreviewLazy(videoId, needsLazyPreview);
  const previewUrl = previewUrlProp || lazyPreview.data?.preview_url || null;
  const resolvedPoster = posterUrl || lazyPreview.data?.poster_url || thumbnailUrls[0] || null;
  const resolvedThumbs =
    thumbnailUrls.length > 0 ? thumbnailUrls : lazyPreview.data?.thumbnail_urls || [];

  // Viewport monitoring (IntersectionObserver)
  useEffect(() => {
    const node = rootRef.current;
    if (!node || autoplayMode !== 'viewport') return;

    const observer = new IntersectionObserver(
      ([entry]) => setInView(entry.isIntersecting && entry.intersectionRatio >= 0.55),
      { threshold: [0, 0.25, 0.55, 0.75, 1] },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [autoplayMode]);

  const stopPreview = useCallback(() => {
    const el = videoRef.current;
    if (el) {
      el.pause();
      el.removeAttribute('src');
      el.load();
    }
    setPhase('poster');
    setFlipIndex(0);
    if (!userUnmuted) setMuted(true);
  }, [userUnmuted]);

  // Activate / deactivate preview playback
  useEffect(() => {
    if (!shouldActivate) {
      stopPreview();
      return;
    }

    if (isDemo) {
      setPhase('flipbook');
      return;
    }

    if (previewUrl) {
      setPhase('loading');
      return;
    }

    if (flipbookFallback && resolvedThumbs.length > 1) {
      setPhase('flipbook');
      return;
    }

    setPhase('poster');
  }, [shouldActivate, isDemo, previewUrl, flipbookFallback, resolvedThumbs.length, stopPreview]);

  // Flipbook animation when no preview clip
  useEffect(() => {
    if (phase !== 'flipbook' || resolvedThumbs.length <= 1) return;
    const id = window.setInterval(() => {
      setFlipIndex((i) => (i + 1) % resolvedThumbs.length);
    }, 900);
    return () => window.clearInterval(id);
  }, [phase, resolvedThumbs.length]);

  // Muted autoplay when preview URL is ready
  useEffect(() => {
    if (phase !== 'loading' || !previewUrl) return;
    const el = videoRef.current;
    if (!el) return;

    el.src = previewUrl;
    el.muted = !userUnmuted;
    el.load();

    const onCanPlay = () => {
      setPhase('video');
      void el.play().catch(() => {
        setPhase(resolvedPoster ? 'poster' : 'flipbook');
      });
    };
    el.addEventListener('canplay', onCanPlay, { once: true });
    return () => el.removeEventListener('canplay', onCanPlay);
  }, [phase, previewUrl, userUnmuted, resolvedPoster]);

  useEffect(() => {
    const el = videoRef.current;
    if (!el || phase !== 'video') return;
    el.muted = !userUnmuted;
  }, [userUnmuted, phase]);

  const activeFlipUrl =
    phase === 'flipbook' && resolvedThumbs.length > 0
      ? resolvedThumbs[flipIndex % resolvedThumbs.length]
      : null;

  const showVideoLayer = phase === 'video' || phase === 'loading';
  const showPosterLayer = !showVideoLayer && (resolvedPoster || activeFlipUrl);

  return (
    <div
      ref={rootRef}
      className={cn('relative aspect-video w-full overflow-hidden', className)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Gradient fallback (demo / no frames yet) */}
      <div
        className={cn(
          'absolute inset-0 transition-opacity duration-300',
          thumbnailGradient || 'bg-thumb-1',
          showPosterLayer || showVideoLayer ? 'opacity-0' : 'opacity-100',
          isDemo && shouldActivate && 'animate-pulseSoft',
        )}
        aria-hidden
      />

      {/* Static poster / flipbook layer */}
      {showPosterLayer ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={activeFlipUrl || resolvedPoster || undefined}
          alt={title ? `${title} preview` : 'Video preview'}
          className={cn(
            'absolute inset-0 h-full w-full object-cover transition-opacity duration-300',
            showVideoLayer ? 'opacity-0' : 'opacity-100',
          )}
          loading="lazy"
        />
      ) : null}

      {/* Muted preview video layer */}
      <video
        ref={videoRef}
        className={cn(
          'absolute inset-0 h-full w-full object-cover transition-opacity duration-300',
          showVideoLayer ? 'opacity-100' : 'opacity-0 pointer-events-none',
        )}
        muted={muted}
        playsInline
        loop
        preload="metadata"
        aria-hidden={!showVideoLayer}
      />

      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/0 to-black/30 pointer-events-none" />

      {phase === 'loading' ? (
        <div className="absolute inset-0 grid place-items-center pointer-events-none">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/20 border-t-white/90" />
        </div>
      ) : null}

      {showMuteToggle && phase === 'video' ? (
        <button
          type="button"
          aria-label={muted ? 'Unmute preview' : 'Mute preview'}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setUserUnmuted(true);
            setMuted((m) => !m);
          }}
          className="absolute bottom-2.5 left-2.5 z-10 grid h-7 w-7 place-items-center rounded-full bg-black/55 text-white/90 ring-1 ring-white/15 hover:bg-black/70"
        >
          {muted ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
        </button>
      ) : null}

      {durationSeconds != null ? (
        <div className="absolute bottom-2.5 right-2.5 rounded bg-black/65 px-1.5 py-0.5 font-mono text-[10px] text-white/90 pointer-events-none">
          {formatPreviewDuration(durationSeconds)}
        </div>
      ) : null}

      {shouldActivate && phase === 'video' ? (
        <div
          className="absolute left-2.5 top-2.5 rounded bg-black/50 px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-white/75 pointer-events-none"
          style={{ '--tw-ring-color': 'rgba(229,9,20,0.4)' } as CSSProperties}
        >
          Preview
        </div>
      ) : null}
    </div>
  );
}

function formatPreviewDuration(seconds: number) {
  const s = Math.max(0, Math.floor(seconds));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${String(r).padStart(2, '0')}`;
}
