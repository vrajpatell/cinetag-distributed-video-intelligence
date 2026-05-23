export const queryKeys = {
  jobs: {
    all: ['jobs'] as const,
    list: (pageSize = 100) => [...queryKeys.jobs.all, 'list', pageSize] as const,
  },
  review: {
    all: ['review'] as const,
    list: (pageSize = 100) => [...queryKeys.review.all, 'list', pageSize] as const,
  },
  search: {
    all: ['search'] as const,
    query: (q: string) => [...queryKeys.search.all, q] as const,
  },
  health: {
    snapshot: ['health', 'snapshot'] as const,
  },
} as const;
