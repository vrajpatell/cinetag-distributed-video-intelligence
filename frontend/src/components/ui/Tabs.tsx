import { useId, type ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/cn';

export interface TabItem {
  id: string;
  label: string;
  badge?: ReactNode;
  disabled?: boolean;
}

export interface TabsProps {
  items: TabItem[];
  value: string;
  onChange: (id: string) => void;
  className?: string;
}

export function Tabs({ items, value, onChange, className }: TabsProps): JSX.Element {
  const groupId = useId();
  return (
    <div role="tablist" aria-orientation="horizontal" className={cn('flex border-b border-bg-3', className)}>
      {items.map((item) => {
        const active = item.id === value;
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            id={`${groupId}-tab-${item.id}`}
            aria-selected={active}
            aria-controls={`${groupId}-panel-${item.id}`}
            disabled={item.disabled}
            onClick={() => onChange(item.id)}
            className={cn(
              'relative flex items-center gap-2 px-4 py-3 text-sm font-semibold tracking-tight transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg-0',
              active ? 'text-text-0' : 'text-text-1 hover:text-text-0',
              item.disabled && 'cursor-not-allowed opacity-50',
            )}
          >
            <span>{item.label}</span>
            {item.badge}
            {active && (
              <motion.span
                layoutId={`tab-underline-${groupId}`}
                className="absolute inset-x-0 -bottom-px h-0.5 bg-accent"
                transition={{ type: 'spring', stiffness: 500, damping: 40 }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
