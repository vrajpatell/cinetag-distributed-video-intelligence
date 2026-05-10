'use client';

/**
 * VideoPlayer
 *
 * Cost-conscious video playback for the CineTag video detail page.
 *
 * Why this is cheap and smooth:
 * - We do NOT pre-fetch the playback URL or any video bytes on initial render.
 *   The component shows a poster (a sampled frame from the pipeline) plus a
 *   play affordance. Bytes are only requested when the user opts in.
 * - On the first play click we ask the API for a short-lived signed GCS URL
 *   (or, in local dev, a Range-aware streaming URL on the API). The browser's
 *   native <video> element then handles seek/buffer via HTTP Range requests
 *   directly against object storage — no Cloud Run egress in production.
 * - `preload="none"` prevents the browser from speculatively pulling the
 *   first few MB before play. That single attribute is the difference
 *   between a free idle page view and tens of MB per visitor.
 * - We deliberately use the native HTMLMediaElement (no hls.js / shaka /
 *   video.js bundle) because the source is a single MP4 and progressive
 *   playback works in every modern browser.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, getVideoPlayback } from '@/lib/api';
import type { VideoPlaybackResponse } from '@/lib/types';

interface VideoPlayerProps {
  videoId: string | number;
  title: string;
  /** Optional poster URL hint; the API will also try to return one. */
  posterUrl?: string | null;
  /**
   * Only render the player UI when we believe a playable asset exists.
   * Demo videos (no real backend row) should set this to false to keep the
   * page rendering its gradient hero instead.
   */
  enabled?: boolean;
}

type LoadState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'ready'; payload: VideoPlaybackResponse }
  | { kind: 'error'; message: string };

export default function VideoPlayer({
  videoId,
  title,
  posterUrl,
  enabled = true,
}: VideoPlayerProps) {
  const [state, setState] = useState<LoadState>({ kind: 'idle' });
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const requestPlayback = useCallback(async () => {
    setState({ kind: 'loading' });
    try {
      const payload = await getVideoPlayback(videoId);
      setState({ kind: 'ready', payload });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.detail || err.message
          : err instanceof Error
            ? err.message
            : 'Could not load video';
      setState({ kind: 'error', message });
    }
  }, [videoId]);

  // When we have the payload we want playback to start automatically — the
  // user already opted in by clicking the poster, so nothing else should be
  // required for them to see the video.
  useEffect(() => {
    if (state.kind !== 'ready') return;
    const el = videoRef.current;
    if (!el) return;
    const playPromise = el.play();
    if (playPromise && typeof playPromise.catch === 'function') {
      playPromise.catch(() => {
        // Autoplay can be blocked (e.g. unmuted audio policies). Native
        // controls are visible so the user can still hit play themselves.
      });
    }
  }, [state]);

  if (!enabled) return null;

  const containerClass =
    'relative aspect-video w-full overflow-hidden rounded-2xl bg-black/80 ring-1 ring-white/10';

  if (state.kind === 'ready') {
    const { payload } = state;
    return (
      <div className={containerClass}>
        {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
        <video
          ref={videoRef}
          className="h-full w-full bg-black"
          src={payload.url}
          poster={payload.poster_url || posterUrl || undefined}
          controls
          playsInline
          preload="metadata"
        >
          <source src={payload.url} type={payload.content_type} />
          Your browser does not support HTML5 video playback.
        </video>
      </div>
    );
  }

  return (
    <div className={containerClass}>
      {posterUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={posterUrl}
          alt={`${title} preview frame`}
          className="absolute inset-0 h-full w-full object-cover opacity-80"
        />
      ) : (
        <div className="absolute inset-0 bg-gradient-to-br from-zinc-900 via-zinc-950 to-black" />
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-black/40" />

      <button
        type="button"
        onClick={requestPlayback}
        disabled={state.kind === 'loading'}
        aria-label={state.kind === 'loading' ? 'Loading video' : `Play ${title}`}
        className="group absolute inset-0 flex items-center justify-center focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70"
      >
        <span
          className={`flex h-20 w-20 items-center justify-center rounded-full bg-white/15 backdrop-blur-md ring-1 ring-white/30 transition group-hover:scale-105 group-hover:bg-white/25 ${
            state.kind === 'loading' ? 'animate-pulse' : ''
          }`}
        >
          {state.kind === 'loading' ? (
            <span className="h-6 w-6 animate-spin rounded-full border-2 border-white/30 border-t-white" />
          ) : (
            <svg
              viewBox="0 0 24 24"
              className="h-9 w-9 translate-x-[2px] fill-white"
              aria-hidden
            >
              <path d="M8 5v14l11-7z" />
            </svg>
          )}
        </span>
      </button>

      {state.kind === 'error' ? (
        <div
          role="alert"
          className="absolute inset-x-3 bottom-3 rounded-md bg-red-950/80 px-3 py-2 text-[12px] text-red-100 ring-1 ring-red-500/40"
        >
          Playback unavailable: {state.message}
        </div>
      ) : (
        <div className="absolute inset-x-4 bottom-4 flex items-center justify-between text-[11px] text-white/70">
          <span className="rounded bg-black/40 px-2 py-1 backdrop-blur-sm">
            Click to play
          </span>
          <span className="rounded bg-black/40 px-2 py-1 font-mono backdrop-blur-sm">
            HTML5 · MP4
          </span>
        </div>
      )}
    </div>
  );
}
