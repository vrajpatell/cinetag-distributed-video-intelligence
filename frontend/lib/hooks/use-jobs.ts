'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ApiError, DEMO_MODE, getJobs, retryJob } from '@/lib/api';
import { DEMO_JOBS } from '@/lib/demo-data';
import { queryKeys } from '@/lib/query-keys';
import type { JobSummary } from '@/lib/types';

export type JobsQueryResult = {
  jobs: JobSummary[];
  usedDemo: boolean;
  loadError: string | null;
};

async function fetchJobs(pageSize: number): Promise<JobsQueryResult> {
  if (DEMO_MODE) {
    return { jobs: DEMO_JOBS, usedDemo: true, loadError: null };
  }
  try {
    const real = await getJobs({ page_size: pageSize });
    if (real.items.length > 0) {
      return { jobs: real.items, usedDemo: false, loadError: null };
    }
    return { jobs: DEMO_JOBS, usedDemo: true, loadError: null };
  } catch (err) {
    return {
      jobs: DEMO_JOBS,
      usedDemo: true,
      loadError:
        err instanceof ApiError
          ? `Could not reach jobs API (${err.status ?? 'network error'}). Showing demo data.`
          : 'Could not reach jobs API. Showing demo data.',
    };
  }
}

export function useJobs(pageSize = 100) {
  return useQuery({
    queryKey: queryKeys.jobs.list(pageSize),
    queryFn: () => fetchJobs(pageSize),
    refetchInterval: 15_000,
  });
}

export function useRetryJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string | number) => {
      if (typeof id === 'string' && id.startsWith('job-')) {
        throw new Error('Retry is disabled for demo jobs.');
      }
      return retryJob(id);
    },
    onSuccess: () => {
      toast.success('Job retry queued');
      void queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all });
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Retry failed');
    },
  });
}
