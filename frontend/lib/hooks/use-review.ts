'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ApiError, getReviewItems, patchTag } from '@/lib/api';
import { DEMO_REVIEW_ITEMS } from '@/lib/demo-data';
import { queryKeys } from '@/lib/query-keys';
import type { ReviewItem } from '@/lib/types';

export type ReviewQueryResult = {
  items: ReviewItem[];
  usedDemo: boolean;
  loadError: string | null;
};

async function fetchReviewItems(pageSize: number): Promise<ReviewQueryResult> {
  try {
    const real = await getReviewItems({ page_size: pageSize });
    if (real.items.length > 0) {
      return { items: real.items, usedDemo: false, loadError: null };
    }
    return { items: DEMO_REVIEW_ITEMS, usedDemo: true, loadError: null };
  } catch (err) {
    return {
      items: DEMO_REVIEW_ITEMS,
      usedDemo: true,
      loadError: err instanceof ApiError ? err.message : 'Could not reach review API.',
    };
  }
}

export function useReviewItems(pageSize = 100) {
  return useQuery({
    queryKey: queryKeys.review.list(pageSize),
    queryFn: () => fetchReviewItems(pageSize),
  });
}

export type TagDecision = 'approved' | 'rejected' | 'edited';

const DECISION_TO_TAG_STATUS: Record<TagDecision, 'approved' | 'rejected'> = {
  approved: 'approved',
  rejected: 'rejected',
  edited: 'approved',
};

export function usePatchTag() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      decision,
      value,
    }: {
      id: ReviewItem['id'];
      decision: TagDecision;
      value?: string;
    }) => {
      if (typeof id !== 'number') {
        return Promise.resolve(null);
      }
      return patchTag(id, {
        status: DECISION_TO_TAG_STATUS[decision],
        tag_value: decision === 'edited' ? value : undefined,
      });
    },
    onSuccess: (_data, vars) => {
      const label =
        vars.decision === 'approved'
          ? 'Tag approved'
          : vars.decision === 'rejected'
            ? 'Tag rejected'
            : 'Tag updated';
      toast.success(label);
      void queryClient.invalidateQueries({ queryKey: queryKeys.review.all });
    },
    onError: (err: Error, vars) => {
      toast.error(`Could not record decision for tag #${vars.id}`, {
        description: err instanceof ApiError ? err.message : err.message,
      });
    },
  });
}
