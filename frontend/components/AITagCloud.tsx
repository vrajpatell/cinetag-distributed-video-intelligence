import type { TagType } from '@/lib/types';

type Tag = { value: string; type: TagType | string; confidence?: number };

const TYPE_CHIP: Record<string, string> = {
  genre: 'chip-red',
  mood: 'chip-violet',
  scene: 'chip-sky',
  object: 'chip-emerald',
  theme: 'chip-amber',
  moderation: 'chip-rose',
  entity: 'chip-neutral',
  language: 'chip-neutral',
};

export default function AITagCloud({
  tags,
  groupByType = true,
}: {
  tags: Tag[];
  groupByType?: boolean;
}) {
  if (!tags || tags.length === 0) return null;
  if (!groupByType) {
    return (
      <div className="flex flex-wrap gap-1.5">
        {tags.map((t, i) => (
          <TagChip key={`${t.value}-${i}`} tag={t} />
        ))}
      </div>
    );
  }
  const groups = new Map<string, Tag[]>();
  for (const t of tags) {
    const key = String(t.type);
    const arr = groups.get(key) || [];
    arr.push(t);
    groups.set(key, arr);
  }
  const entries = Array.from(groups.entries()).sort();
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      {entries.map(([type, ts]) => (
        <div key={type} className="panel-muted p-3">
          <div className="mb-2 flex items-center justify-between">
            <div className="text-[11px] uppercase tracking-wider text-white/50">{type}</div>
            <div className="text-[11px] text-white/40">{ts.length}</div>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {ts.map((t, i) => (
              <TagChip key={`${t.value}-${i}`} tag={t} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function TagChip({ tag }: { tag: Tag }) {
  const cls = TYPE_CHIP[String(tag.type)] || 'chip-neutral';
  return (
    <span className={cls}>
      {tag.value}
      {tag.confidence != null ? (
        <>
          <span className="text-white/30">·</span>
          <span className="font-mono text-white/65">{tag.confidence.toFixed(2)}</span>
        </>
      ) : null}
    </span>
  );
}
