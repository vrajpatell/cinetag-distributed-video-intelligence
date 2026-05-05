type Variant = 'default' | 'compact';

const STATUS_MAP: Record<
  string,
  { label: string; cls: string; dot?: string }
> = {
  queued: { label: 'queued', cls: 'chip-neutral', dot: 'bg-white/50' },
  running: { label: 'running', cls: 'chip-sky', dot: 'bg-sky-400' },
  processing: { label: 'processing', cls: 'chip-sky', dot: 'bg-sky-400' },
  completed: { label: 'completed', cls: 'chip-emerald', dot: 'bg-emerald-400' },
  failed: { label: 'failed', cls: 'chip-rose', dot: 'bg-rose-400' },
  partially_completed: {
    label: 'partial',
    cls: 'chip-amber',
    dot: 'bg-amber-400',
  },
  upload_pending: { label: 'awaiting upload', cls: 'chip-neutral' },
  uploaded: { label: 'uploaded', cls: 'chip-sky', dot: 'bg-sky-400' },
  review_ready: { label: 'review_ready', cls: 'chip-violet', dot: 'bg-violet-400' },
  published: { label: 'published', cls: 'chip-emerald', dot: 'bg-emerald-400' },
  unknown: { label: 'unknown', cls: 'chip-neutral' },
};

const STAGE_MAP: Record<string, string> = {
  queued: 'queued',
  metadata_extraction: 'metadata',
  frame_sampling: 'frames',
  scene_segmentation: 'scenes',
  transcription: 'transcript',
  llm_tagging: 'llm tags',
  embedding: 'embeddings',
  review_ready: 'review',
  completed: 'completed',
};

export default function JobStatusBadge({
  status,
  stage,
  compact = false,
}: {
  status?: string;
  stage?: string;
  compact?: boolean | Variant;
}) {
  const isCompact = compact === true || compact === 'compact';
  const sizeCls = isCompact ? '!text-[10px] !px-1.5 !py-0.5' : '';
  if (status) {
    const s = STATUS_MAP[status] || STATUS_MAP.unknown;
    return (
      <span className={`${s.cls} ${sizeCls}`}>
        {s.dot ? <span className={`h-1.5 w-1.5 rounded-full ${s.dot} animate-pulseSoft`} /> : null}
        {s.label}
      </span>
    );
  }
  if (stage) {
    const label = STAGE_MAP[stage] || stage;
    const isLLM = stage === 'llm_tagging';
    const cls = isLLM
      ? 'chip-amber'
      : stage === 'completed'
        ? 'chip-emerald'
        : stage === 'failed'
          ? 'chip-rose'
          : 'chip-sky';
    return (
      <span className={`${cls} ${sizeCls}`}>
        <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70 animate-pulseSoft" />
        {label}
      </span>
    );
  }
  return <span className={`chip-neutral ${sizeCls}`}>—</span>;
}
