import { API_BASE_URL } from '@/state/api';

const BUILD_SHA = (import.meta.env.VITE_BUILD_SHA as string | undefined) ?? 'dev';

export function Footer(): JSX.Element {
  return (
    <footer className="mt-24 border-t border-bg-3 bg-bg-0">
      <div className="mx-auto flex max-w-rail flex-col gap-2 px-4 py-8 text-xs text-text-2 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-12">
        <p>© {new Date().getFullYear()} CineTag · Distributed Video Intelligence</p>
        <p className="font-mono">
          build <span className="text-text-1">{BUILD_SHA.slice(0, 7)}</span>
          <span className="mx-2 text-bg-3">·</span>
          api <span className="text-text-1">{stripScheme(API_BASE_URL)}</span>
        </p>
      </div>
    </footer>
  );
}

function stripScheme(url: string): string {
  return url.replace(/^https?:\/\//, '');
}
