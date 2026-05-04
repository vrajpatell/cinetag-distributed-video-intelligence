import { useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query';
import { api } from '@/state/api';
import { UploadResponseSchema, type UploadResponse } from '@/lib/zodSchemas';
import { videosKey } from '@/state/hooks/useVideos';
import { jobsKey } from '@/state/hooks/useJobs';

export interface UploadVideoInput {
  file: File;
  title?: string;
  onProgress?: (percent: number) => void;
}

export function useUploadVideo(): UseMutationResult<UploadResponse, Error, UploadVideoInput> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ file, title, onProgress }) => {
      const form = new FormData();
      form.append('file', file);
      if (title) form.append('title', title);
      const { data } = await api.post('/api/videos/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 0,
        onUploadProgress: (e) => {
          if (!onProgress) return;
          const total = e.total ?? file.size ?? 1;
          const pct = total > 0 ? Math.round((e.loaded / total) * 100) : 0;
          onProgress(pct);
        },
      });
      return UploadResponseSchema.parse(data);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: videosKey });
      qc.invalidateQueries({ queryKey: jobsKey });
    },
  });
}
