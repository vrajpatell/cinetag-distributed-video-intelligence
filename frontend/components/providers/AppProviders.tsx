'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import { Toaster } from 'sonner';

export default function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 10_000,
            retry: 1,
            refetchOnWindowFocus: true,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster
        theme="dark"
        position="bottom-right"
        toastOptions={{
          classNames: {
            toast:
              'group toast !bg-cinetag-panel !border-cinetag-border !text-cinetag-text shadow-card',
            title: '!text-white',
            description: '!text-white/65',
            success: '!border-emerald-500/40',
            error: '!border-rose-500/40',
          },
        }}
      />
    </QueryClientProvider>
  );
}
