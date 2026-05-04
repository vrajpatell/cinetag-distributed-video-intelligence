import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/cn';

export interface CarouselProps {
  title: string;
  description?: string;
  children: ReactNode;
  emptyMessage?: ReactNode;
  cta?: ReactNode;
  className?: string;
}

export function Carousel({
  title,
  description,
  children,
  emptyMessage,
  cta,
  className,
}: CarouselProps): JSX.Element {
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const [mounted, setMounted] = useState(false);
  const [canLeft, setCanLeft] = useState(false);
  const [canRight, setCanRight] = useState(false);

  useEffect(() => {
    if (!scrollerRef.current) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            setMounted(true);
            observer.disconnect();
            break;
          }
        }
      },
      { rootMargin: '200px' },
    );
    observer.observe(scrollerRef.current);
    return () => observer.disconnect();
  }, []);

  const updateBounds = useCallback(() => {
    const el = scrollerRef.current;
    if (!el) return;
    setCanLeft(el.scrollLeft > 4);
    setCanRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 4);
  }, []);

  useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;
    updateBounds();
    el.addEventListener('scroll', updateBounds, { passive: true });
    const ro = new ResizeObserver(updateBounds);
    ro.observe(el);
    return () => {
      el.removeEventListener('scroll', updateBounds);
      ro.disconnect();
    };
  }, [updateBounds, mounted]);

  const scrollByDir = (dir: -1 | 1) => {
    const el = scrollerRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * (el.clientWidth - 80), behavior: 'smooth' });
  };

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      scrollByDir(1);
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      scrollByDir(-1);
    }
  };

  return (
    <section className={cn('group/section relative pb-3 pt-6', className)}>
      <div className="mb-3 flex items-end justify-between gap-4 px-4 sm:px-6 lg:px-12">
        <div>
          <h2 className="font-display text-xl font-bold tracking-tightest text-text-0 sm:text-2xl">
            {title}
          </h2>
          {description && <p className="mt-0.5 text-sm text-text-1">{description}</p>}
        </div>
        {cta}
      </div>

      <div className="relative">
        {emptyMessage ? (
          <div className="px-4 sm:px-6 lg:px-12">
            <div className="rounded-md border border-dashed border-bg-3 bg-bg-1 px-4 py-8 text-sm text-text-2">
              {emptyMessage}
            </div>
          </div>
        ) : (
          <>
            <button
              type="button"
              aria-label="Scroll left"
              onClick={() => scrollByDir(-1)}
              className={cn(
                'absolute left-2 top-1/2 z-10 hidden h-12 w-9 -translate-y-1/2 items-center justify-center rounded-r-md bg-black/70 text-text-0 transition-opacity hover:bg-black/90 focus-visible:opacity-100 sm:flex',
                canLeft
                  ? 'opacity-0 group-hover/section:opacity-100 focus:opacity-100'
                  : 'pointer-events-none opacity-0',
              )}
            >
              <ChevronLeft className="h-5 w-5" aria-hidden />
            </button>
            <button
              type="button"
              aria-label="Scroll right"
              onClick={() => scrollByDir(1)}
              className={cn(
                'absolute right-2 top-1/2 z-10 hidden h-12 w-9 -translate-y-1/2 items-center justify-center rounded-l-md bg-black/70 text-text-0 transition-opacity hover:bg-black/90 focus-visible:opacity-100 sm:flex',
                canRight
                  ? 'opacity-0 group-hover/section:opacity-100 focus:opacity-100'
                  : 'pointer-events-none opacity-0',
              )}
            >
              <ChevronRight className="h-5 w-5" aria-hidden />
            </button>

            <div
              ref={scrollerRef}
              role="region"
              aria-label={title}
              tabIndex={0}
              onKeyDown={onKeyDown}
              className={cn(
                'scrollbar-hide flex snap-x snap-mandatory gap-3 overflow-x-auto scroll-smooth px-4 py-3 sm:px-6 lg:px-12',
                'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg-0',
              )}
            >
              {mounted ? (
                children
              ) : (
                <div className="h-[135px]" aria-hidden />
              )}
            </div>
          </>
        )}
      </div>
    </section>
  );
}
