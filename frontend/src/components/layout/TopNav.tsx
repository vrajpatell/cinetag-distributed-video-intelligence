import { useEffect, useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { Bell, Menu, Search } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/cn';

const NAV_ITEMS = [
  { to: '/', label: 'Browse', end: true },
  { to: '/search', label: 'Search' },
  { to: '/upload', label: 'Upload' },
  { to: '/jobs', label: 'Jobs' },
  { to: '/review', label: 'Review' },
] as const;

export function TopNav(): JSX.Element {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header
      className={cn(
        'fixed inset-x-0 top-0 z-40 transition-colors duration-200',
        scrolled
          ? 'border-b border-bg-3 bg-black'
          : 'bg-gradient-to-b from-black/80 via-black/40 to-transparent backdrop-blur-sm',
      )}
    >
      <div className="mx-auto flex h-16 max-w-rail items-center gap-6 px-4 sm:px-6 lg:px-12">
        <Link
          to="/"
          aria-label="CineTag home"
          className="font-display text-xl font-black tracking-[0.15em] text-accent sm:text-2xl"
        >
          CINETAG
        </Link>

        <nav aria-label="Primary" className="hidden items-center gap-5 lg:flex">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={'end' in item ? item.end : false}
              className={({ isActive }) =>
                cn(
                  'text-sm font-medium tracking-tight transition-colors',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg-0 rounded-sm',
                  isActive ? 'text-text-0' : 'text-text-1 hover:text-text-0',
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            onClick={() => navigate('/search')}
            aria-label="Search"
            className="rounded-md p-2 text-text-1 transition-colors hover:bg-bg-2 hover:text-text-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            <Search className="h-5 w-5" aria-hidden />
          </button>
          <button
            type="button"
            aria-label="Notifications"
            className="rounded-md p-2 text-text-1 transition-colors hover:bg-bg-2 hover:text-text-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            <Bell className="h-5 w-5" aria-hidden />
          </button>
          <span
            aria-hidden
            className="ml-1 hidden h-9 w-9 select-none items-center justify-center rounded-md bg-accent text-sm font-bold text-white sm:inline-flex"
            title="CT"
          >
            CT
          </span>
          <button
            type="button"
            onClick={() => setMobileOpen((v) => !v)}
            aria-label="Toggle navigation"
            aria-expanded={mobileOpen}
            className="ml-1 rounded-md p-2 text-text-1 transition-colors hover:bg-bg-2 hover:text-text-0 lg:hidden"
          >
            <Menu className="h-5 w-5" aria-hidden />
          </button>
        </div>
      </div>
      {mobileOpen && (
        <motion.nav
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          aria-label="Mobile primary"
          className="border-t border-bg-3 bg-black px-4 py-3 lg:hidden"
        >
          <div className="flex flex-col gap-1">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={'end' in item ? item.end : false}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  cn(
                    'rounded-md px-3 py-2 text-sm font-medium',
                    isActive ? 'bg-bg-2 text-text-0' : 'text-text-1 hover:bg-bg-2 hover:text-text-0',
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        </motion.nav>
      )}
    </header>
  );
}
