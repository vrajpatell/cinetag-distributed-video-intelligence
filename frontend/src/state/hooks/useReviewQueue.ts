import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { z } from 'zod';
import { api } from '@/state/api';
import {
  GeneratedTagSchema,
  VideoAssetSchema,
  type GeneratedTag,
  type VideoAsset,
} from '@/lib/zodSchemas';

const VideoArray = z.array(VideoAssetSchema);
const TagArray = z.array(GeneratedTagSchema);

export interface ReviewItem {
  tag: GeneratedTag;
  video: VideoAsset;
}

async function fetchPendingTags(): Promise<ReviewItem[]> {
  const { data: videosData } = await api.get('/api/videos');
  const videos = VideoArray.parse(videosData);
  const tagBatches = await Promise.all(
    videos.map(async (v) => {
      try {
        const { data } = await api.get(`/api/videos/${v.id}/tags`);
        const tags = TagArray.parse(data);
        return tags.map((t) => ({ tag: t, video: v }));
      } catch {
        return [] as ReviewItem[];
      }
    }),
  );
  return tagBatches
    .flat()
    .filter((item) => item.tag.status === 'pending_review')
    .sort((a, b) => (a.tag.created_at < b.tag.created_at ? 1 : -1));
}

export function useReviewQueue(): UseQueryResult<ReviewItem[]> {
  return useQuery({
    queryKey: ['review-queue'],
    queryFn: fetchPendingTags,
    staleTime: 10_000,
  });
}
