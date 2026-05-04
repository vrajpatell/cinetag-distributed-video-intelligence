import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { z } from 'zod';
import { api } from '@/state/api';
import {
  FrameSampleSchema,
  GeneratedTagSchema,
  SceneSegmentSchema,
  TranscriptSchema,
  type FrameSample,
  type GeneratedTag,
  type SceneSegment,
  type Transcript,
} from '@/lib/zodSchemas';

const FrameArray = z.array(FrameSampleSchema);
const SceneArray = z.array(SceneSegmentSchema);
const TagArray = z.array(GeneratedTagSchema);

export function useFrames(videoId: number | undefined): UseQueryResult<FrameSample[]> {
  return useQuery({
    queryKey: ['video', videoId, 'frames'],
    enabled: videoId != null && Number.isFinite(videoId),
    queryFn: async () => {
      const { data } = await api.get(`/api/videos/${videoId}/frames`);
      return FrameArray.parse(data);
    },
  });
}

export function useScenes(videoId: number | undefined): UseQueryResult<SceneSegment[]> {
  return useQuery({
    queryKey: ['video', videoId, 'scenes'],
    enabled: videoId != null && Number.isFinite(videoId),
    queryFn: async () => {
      const { data } = await api.get(`/api/videos/${videoId}/scenes`);
      return SceneArray.parse(data);
    },
  });
}

export function useTranscript(videoId: number | undefined): UseQueryResult<Transcript> {
  return useQuery({
    queryKey: ['video', videoId, 'transcript'],
    enabled: videoId != null && Number.isFinite(videoId),
    queryFn: async () => {
      const { data } = await api.get(`/api/videos/${videoId}/transcript`);
      if (data == null || data === '') return null;
      return TranscriptSchema.parse(data);
    },
  });
}

export function useTagsByVideo(videoId: number | undefined): UseQueryResult<GeneratedTag[]> {
  return useQuery({
    queryKey: ['video', videoId, 'tags'],
    enabled: videoId != null && Number.isFinite(videoId),
    queryFn: async () => {
      const { data } = await api.get(`/api/videos/${videoId}/tags`);
      return TagArray.parse(data);
    },
  });
}
