import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { z } from 'zod';
import { api } from '@/state/api';
import { SearchResultSchema, type SearchResult } from '@/lib/zodSchemas';

const ResultArray = z.array(SearchResultSchema);

export interface SemanticSearchFilters {
  tag_type?: string;
  status?: string;
  duration_min?: number;
  duration_max?: number;
}

export interface SemanticSearchInput extends SemanticSearchFilters {
  query: string;
}

export function useSemanticSearch(input: SemanticSearchInput): UseQueryResult<SearchResult[]> {
  const trimmed = input.query.trim();
  const enabled = trimmed.length > 0;
  return useQuery({
    queryKey: ['semantic-search', trimmed, input.tag_type, input.status, input.duration_min, input.duration_max],
    enabled,
    queryFn: async ({ signal }) => {
      const body: Record<string, unknown> = { query: trimmed };
      if (input.tag_type) body.tag_type = input.tag_type;
      if (input.status) body.status = input.status;
      if (input.duration_min != null) body.duration_min = input.duration_min;
      if (input.duration_max != null) body.duration_max = input.duration_max;
      const { data } = await api.post('/api/search/semantic', body, { signal });
      return ResultArray.parse(data);
    },
    staleTime: 15_000,
  });
}
