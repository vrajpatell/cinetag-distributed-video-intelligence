'use client';

import { useQuery } from '@tanstack/react-query';
import { getVideoPreview } from '@/lib/api';

export function useVideoPreviewLazy(videoId: number | string | undefined, enabled: boolean) {
  const numericId = typeof videoId === 'number' ? videoId : undefined;
  const canFetch = enabled && numericId != null && !Number.isNaN(numericId);

  return useQuery({
    queryKey: ['video-preview', numericId],
    queryFn: () => getVideoPreview(numericId!),
    enabled: canFetch,
    staleTime: 45 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  });
}
