import { Check, X } from 'lucide-react';
import { cn } from '@/lib/cn';
import type { GeneratedTag } from '@/lib/zodSchemas';

export interface TagChipProps {
  tag: GeneratedTag;
  onApprove?: () => void;
  onReject?: () => void;
  className?: string;
}

function confidenceClasses(confidence: number | null | undefined): string {
  const c = confidence ?? 0;
  if (c >= 0.85) return 'border-success/50 bg-success/10 text-success';
  if (c >= 0.6) return 'border-warning/50 bg-warning/10 text-warning';
  return 'border-bg-3 bg-bg-2 text-text-1';
}

export function TagChip({ tag, onApprove, onReject, className }: TagChipProps): JSX.Element {
  const isPending = tag.status === 'pending_review';
  const isApproved = tag.status === 'approved';
  const isRejected = tag.status === 'rejected';
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium tracking-tight transition-colors',
        confidenceClasses(tag.confidence),
        isApproved && 'border-success bg-success/20 text-success',
        isRejected && 'border-accent/60 bg-accent/20 text-accent line-through opacity-80',
        className,
      )}
      title={tag.rationale ?? undefined}
    >
      <span className="text-text-2 normal-case">{tag.tag_type}</span>
      <span className="text-text-0">{tag.tag_value}</span>
      {tag.confidence != null && (
        <span className="text-text-2">{Math.round(tag.confidence * 100)}%</span>
      )}
      {isPending && (
        <span className="ml-1 flex items-center gap-1">
          {onApprove && (
            <button
              type="button"
              onClick={onApprove}
              aria-label={`Approve ${tag.tag_value}`}
              className="rounded-full p-0.5 text-text-1 transition-colors hover:bg-success/30 hover:text-success focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              <Check className="h-3.5 w-3.5" aria-hidden />
            </button>
          )}
          {onReject && (
            <button
              type="button"
              onClick={onReject}
              aria-label={`Reject ${tag.tag_value}`}
              className="rounded-full p-0.5 text-text-1 transition-colors hover:bg-accent/30 hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              <X className="h-3.5 w-3.5" aria-hidden />
            </button>
          )}
        </span>
      )}
    </span>
  );
}
