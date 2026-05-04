import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/cn';

export type BadgeTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger' | 'accent';

const toneClasses: Record<BadgeTone, string> = {
  neutral: 'bg-bg-3 text-text-1',
  info: 'bg-blue-500/15 text-blue-300 ring-1 ring-inset ring-blue-500/30',
  success: 'bg-success/15 text-success ring-1 ring-inset ring-success/30',
  warning: 'bg-warning/15 text-warning ring-1 ring-inset ring-warning/30',
  danger: 'bg-accent/15 text-accent ring-1 ring-inset ring-accent/30',
  accent: 'bg-accent text-white',
};

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
  children: ReactNode;
}

export function Badge({ tone = 'neutral', className, children, ...rest }: BadgeProps): JSX.Element {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium tracking-tight',
        toneClasses[tone],
        className,
      )}
      {...rest}
    >
      {children}
    </span>
  );
}

export function jobStatusTone(status: string): BadgeTone {
  switch (status) {
    case 'succeeded':
      return 'success';
    case 'running':
      return 'info';
    case 'queued':
      return 'neutral';
    case 'failed':
      return 'danger';
    case 'cancelled':
      return 'warning';
    default:
      return 'neutral';
  }
}

export function tagStatusTone(status: string): BadgeTone {
  switch (status) {
    case 'approved':
      return 'success';
    case 'rejected':
      return 'danger';
    case 'pending_review':
      return 'warning';
    default:
      return 'neutral';
  }
}
