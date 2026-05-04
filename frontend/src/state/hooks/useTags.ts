import { useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query';
import { api } from '@/state/api';
import { GeneratedTagSchema, type GeneratedTag } from '@/lib/zodSchemas';
import { toast } from '@/components/ui/toastStore';

export interface PatchTagInput {
  tagId: number;
  videoId?: number;
  status?: 'pending_review' | 'approved' | 'rejected';
  tag_value?: string;
}

export function usePatchTag(): UseMutationResult<GeneratedTag, Error, PatchTagInput> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ tagId, status, tag_value }) => {
      const body: Record<string, string> = {};
      if (status) body.status = status;
      if (tag_value != null) body.tag_value = tag_value;
      const { data } = await api.patch(`/api/tags/${tagId}`, body);
      return GeneratedTagSchema.parse(data);
    },
    onSuccess: (data, variables) => {
      const vid = variables.videoId ?? data.video_id;
      qc.invalidateQueries({ queryKey: ['video', vid, 'tags'] });
      qc.invalidateQueries({ queryKey: ['review-queue'] });
    },
    onError: (err) => {
      toast.danger('Failed to update tag', err.message);
    },
  });
}

export interface ManualTagInput {
  videoId: number;
  tag_type: string;
  tag_value: string;
  confidence?: number;
}

export function useAddManualTag(): UseMutationResult<GeneratedTag, Error, ManualTagInput> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ videoId, tag_type, tag_value, confidence }) => {
      const { data } = await api.post(`/api/videos/${videoId}/tags/manual`, {
        tag_type,
        tag_value,
        confidence: confidence ?? 1.0,
      });
      return GeneratedTagSchema.parse(data);
    },
    onSuccess: (_data, variables) => {
      toast.success('Tag added', `${variables.tag_type}: ${variables.tag_value}`);
      qc.invalidateQueries({ queryKey: ['video', variables.videoId, 'tags'] });
    },
  });
}
