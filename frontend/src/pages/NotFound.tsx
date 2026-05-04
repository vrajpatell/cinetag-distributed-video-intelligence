import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/Button';

export default function NotFoundPage(): JSX.Element {
  return (
    <div className="mx-auto flex min-h-[70vh] max-w-2xl flex-col items-center justify-center gap-4 px-4 text-center sm:px-6">
      <p className="font-display text-7xl font-black tracking-tightest text-accent">404</p>
      <h1 className="font-display text-2xl font-bold tracking-tight text-text-0 sm:text-3xl">
        Lost in the carousel.
      </h1>
      <p className="max-w-md text-sm text-text-1">
        The page you tried to open doesn't exist, or has been removed. Head back to browse and pick something else.
      </p>
      <div className="flex gap-3">
        <Link to="/">
          <Button variant="primary">Back to browse</Button>
        </Link>
        <Link to="/upload">
          <Button variant="secondary">Upload a video</Button>
        </Link>
      </div>
    </div>
  );
}
