import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { api } from '@/state/api';
import { VideoAssetSchema, type VideoAsset } from '@/lib/zodSchemas';
import { z } from 'zod';

const VideoArraySchema = z.array(VideoAssetSchema);

export const videosKey = ['videos'] as const;

export function useVideos(): UseQueryResult<VideoAsset[]> {
  return useQuery({
    queryKey: videosKey,
    queryFn: async () => {
      const { data } = await api.get('/api/videos');
      return VideoArraySchema.parse(data);
    },
  });
}

export function useVideo(id: number | string | undefined): UseQueryResult<VideoAsset> {
  const numericId = typeof id === 'string' ? Number(id) : id;
  return useQuery({
    queryKey: ['video', numericId],
    enabled: numericId != null && Number.isFinite(numericId),
    queryFn: async () => {
      const { data } = await api.get(`/api/videos/${numericId}`);
      return VideoAssetSchema.parse(data);
    },
  });
}
