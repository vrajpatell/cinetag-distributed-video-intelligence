import { AlertTriangle, Check, Circle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/cn';
import { humanizeMs } from '@/lib/format';
import type { ProcessingStageRun } from '@/lib/zodSchemas';

export interface PipelineStep {
  name: string;
  status: 'pending' | 'running' | 'succeeded' | 'failed' | 'skipped';
  durationMs?: number | null;
  error?: string | null;
  startedAt?: string | null;
}

export interface PipelineStepperProps {
  steps: PipelineStep[];
  className?: string;
}

const DEFAULT_STAGES = [
  'queued',
  'probe',
  'sample_frames',
  'transcribe',
  'detect_scenes',
  'tag',
  'embed',
  'finalize',
];

export function deriveStepsFromJob(
  currentStage: string | null | undefined,
  status: string,
): PipelineStep[] {
  const idx = currentStage ? DEFAULT_STAGES.indexOf(currentStage) : -1;
  const safeIdx = idx === -1 ? (status === 'queued' ? 0 : DEFAULT_STAGES.length - 1) : idx;

  return DEFAULT_STAGES.map((name, i) => {
    if (status === 'failed' && i === safeIdx) {
      return { name, status: 'failed' as const };
    }
    if (i < safeIdx) return { name, status: 'succeeded' as const };
    if (i === safeIdx && status === 'running') return { name, status: 'running' as const };
    if (status === 'succeeded') return { name, status: 'succeeded' as const };
    return { name, status: 'pending' as const };
  });
}

export function stageRunsToSteps(runs: ProcessingStageRun[]): PipelineStep[] {
  return runs.map((r) => ({
    name: r.stage_name,
    status:
      r.status === 'succeeded'
        ? 'succeeded'
        : r.status === 'failed'
          ? 'failed'
          : r.status === 'running'
            ? 'running'
            : r.status === 'skipped'
              ? 'skipped'
              : 'pending',
    durationMs: r.duration_ms ?? null,
    error: r.error_message ?? null,
    startedAt: r.started_at ?? null,
  }));
}

export function PipelineStepper({ steps, className }: PipelineStepperProps): JSX.Element {
  return (
    <ol className={cn('relative space-y-1', className)} aria-label="Pipeline stages">
      {steps.map((step, i) => {
        const isLast = i === steps.length - 1;
        return (
          <li key={`${step.name}-${i}`} className="relative pl-10">
            {!isLast && (
              <span
                aria-hidden
                className={cn(
                  'absolute left-[15px] top-7 h-[calc(100%-12px)] w-px',
                  step.status === 'succeeded' ? 'bg-success/40' : 'bg-bg-3',
                )}
              />
            )}
            <span
              className={cn(
                'absolute left-0 top-1 inline-flex h-8 w-8 items-center justify-center rounded-full border',
                step.status === 'succeeded' && 'border-success/60 bg-success/15 text-success',
                step.status === 'running' && 'border-blue-500/60 bg-blue-500/15 text-blue-300',
                step.status === 'failed' && 'border-accent/60 bg-accent/15 text-accent',
                (step.status === 'pending' || step.status === 'skipped') && 'border-bg-3 bg-bg-1 text-text-2',
              )}
            >
              {step.status === 'succeeded' && <Check className="h-4 w-4" aria-hidden />}
              {step.status === 'running' && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
              {step.status === 'failed' && <AlertTriangle className="h-4 w-4" aria-hidden />}
              {(step.status === 'pending' || step.status === 'skipped') && (
                <Circle className="h-3 w-3" aria-hidden />
              )}
            </span>
            <div className="rounded-md border border-bg-3 bg-bg-1 px-4 py-3">
              <div className="flex items-center justify-between gap-2">
                <p className="font-medium text-text-0 capitalize">{step.name.replaceAll('_', ' ')}</p>
                <span
                  className={cn(
                    'text-xs',
                    step.status === 'failed' ? 'text-accent' : 'text-text-2',
                  )}
                >
                  {step.status === 'pending' || step.status === 'skipped'
                    ? '—'
                    : humanizeMs(step.durationMs ?? null)}
                </span>
              </div>
              {step.error && (
                <p className="mt-1 text-xs text-accent">{step.error}</p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
