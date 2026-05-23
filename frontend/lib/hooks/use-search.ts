'use client';

import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { searchVideos } from '@/lib/api';
import { DEMO_SEARCH_RESULTS } from '@/lib/demo-data';
import type { SearchResult } from '@/lib/types';

export type SearchMutationResult = {
  results: SearchResult[];
  usedDemo: boolean;
  error: string | null;
};

export function useSemanticSearch() {
  return useMutation({
    mutationFn: async (query: string): Promise<SearchMutationResult> => {
      try {
        const r = await searchVideos({ query });
        if (Array.isArray(r) && r.length > 0) {
          return { results: r, usedDemo: false, error: null };
        }
        return {
          results: DEMO_SEARCH_RESULTS,
          usedDemo: true,
          error: null,
        };
      } catch (err) {
        return {
          results: DEMO_SEARCH_RESULTS,
          usedDemo: true,
          error: err instanceof Error ? err.message : 'Search failed; showing demo results.',
        };
      }
    },
    onError: () => {
      toast.error('Semantic search failed');
    },
  });
}
