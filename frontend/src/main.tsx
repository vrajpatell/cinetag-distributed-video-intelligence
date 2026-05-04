import { StrictMode, lazy } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { AppShell } from '@/components/layout/AppShell';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { Toaster } from '@/components/ui/Toaster';
import { queryClient } from '@/state/queryClient';
import { apiOrigin } from '@/state/api';
import '@/styles/globals.css';

if (typeof document !== 'undefined' && apiOrigin) {
  try {
    const url = new URL(apiOrigin);
    if (url.origin !== window.location.origin) {
      const link = document.createElement('link');
      link.rel = 'preconnect';
      link.href = url.origin;
      link.crossOrigin = 'anonymous';
      document.head.appendChild(link);
    }
  } catch {
    /* ignore malformed VITE_API_BASE_URL */
  }
}

const BrowsePage = lazy(() => import('@/pages/Dashboard'));
const SearchPage = lazy(() => import('@/pages/SemanticSearch'));
const UploadPage = lazy(() => import('@/pages/Upload'));
const VideoDetailPage = lazy(() => import('@/pages/VideoDetail'));
const JobsPage = lazy(() => import('@/pages/Jobs'));
const JobDetailPage = lazy(() => import('@/pages/JobDetail'));
const ReviewQueuePage = lazy(() => import('@/pages/ReviewQueue'));
const NotFoundPage = lazy(() => import('@/pages/NotFound'));

const rootElement = document.getElementById('root');
if (!rootElement) throw new Error('#root not found');

createRoot(rootElement).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route element={<AppShell />}>
              <Route path="/" element={<BrowsePage />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/videos/:id" element={<VideoDetailPage />} />
              <Route path="/jobs" element={<JobsPage />} />
              <Route path="/jobs/:id" element={<JobDetailPage />} />
              <Route path="/review" element={<ReviewQueuePage />} />
              <Route path="/dashboard" element={<Navigate to="/" replace />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster />
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>,
);
