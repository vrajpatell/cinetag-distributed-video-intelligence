import { useMutation, useQuery, useQueryClient, type UseMutationResult, type UseQueryResult } from '@tanstack/react-query';
import { z } from 'zod';
import { api } from '@/state/api';
import {
  ProcessingJobSchema,
  RetryResponseSchema,
  type ProcessingJob,
  type RetryResponse,
} from '@/lib/zodSchemas';
import { toast } from '@/components/ui/toastStore';

const JobArraySchema = z.array(ProcessingJobSchema);

const TERMINAL_STATUSES = new Set(['succeeded', 'failed', 'cancelled']);

export const jobsKey = ['jobs'] as const;

export function useJobs(): UseQueryResult<ProcessingJob[]> {
  return useQuery({
    queryKey: jobsKey,
    queryFn: async () => {
      const { data } = await api.get('/api/jobs');
      return JobArraySchema.parse(data);
    },
    refetchInterval: (query) => {
      const data = query.state.data as ProcessingJob[] | undefined;
      if (!data) return false;
      const hasActive = data.some((j) => !TERMINAL_STATUSES.has(j.status));
      return hasActive ? 5_000 : false;
    },
  });
}

export function useJob(id: number | string | undefined): UseQueryResult<ProcessingJob> {
  const numericId = typeof id === 'string' ? Number(id) : id;
  return useQuery({
    queryKey: ['job', numericId],
    enabled: numericId != null && Number.isFinite(numericId),
    queryFn: async () => {
      const { data } = await api.get(`/api/jobs/${numericId}`);
      return ProcessingJobSchema.parse(data);
    },
    refetchInterval: (query) => {
      const data = query.state.data as ProcessingJob | undefined;
      if (!data) return false;
      return TERMINAL_STATUSES.has(data.status) ? false : 4_000;
    },
  });
}

export function useRetryJob(jobId: number | undefined): UseMutationResult<RetryResponse, Error, void> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      if (jobId == null) throw new Error('No job id');
      const { data } = await api.post(`/api/jobs/${jobId}/retry`);
      return RetryResponseSchema.parse(data);
    },
    onSuccess: () => {
      toast.success('Retry queued', `Job #${jobId} has been re-queued.`);
      qc.invalidateQueries({ queryKey: ['job', jobId] });
      qc.invalidateQueries({ queryKey: jobsKey });
    },
  });
}
