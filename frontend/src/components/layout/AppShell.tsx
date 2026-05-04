import { Suspense, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { TopNav } from '@/components/layout/TopNav';
import { Footer } from '@/components/layout/Footer';
import { Skeleton } from '@/components/ui/Skeleton';

function PageSpinner(): JSX.Element {
  return (
    <div className="mx-auto max-w-rail px-4 py-12 sm:px-6 lg:px-12">
      <Skeleton className="h-[40vh] w-full" />
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="aspect-video w-full" />
        ))}
      </div>
    </div>
  );
}

export function AppShell(): JSX.Element {
  const location = useLocation();
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'auto' });
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen flex-col bg-bg-0">
      <TopNav />
      <main id="main" className="flex-1 pt-16">
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
        >
          <Suspense fallback={<PageSpinner />}>
            <Outlet />
          </Suspense>
        </motion.div>
      </main>
      <Footer />
    </div>
  );
}
