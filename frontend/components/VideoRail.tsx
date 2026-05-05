import type { VideoSummary } from '@/lib/types';
import VideoCard from './VideoCard';

export default function VideoRail({
  title,
  subtitle,
  videos,
  accent = 'red',
}: {
  title: string;
  subtitle?: string;
  videos: VideoSummary[];
  accent?: 'red' | 'sky' | 'emerald' | 'amber' | 'violet';
}) {
  if (!videos || videos.length === 0) return null;
  const accentClass: Record<string, string> = {
    red: 'before:bg-cinetag-red',
    sky: 'before:bg-sky-400',
    emerald: 'before:bg-emerald-400',
    amber: 'before:bg-amber-400',
    violet: 'before:bg-violet-400',
  };
  return (
    <section className="mx-auto w-full max-w-[1400px] px-5">
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <h2
            className={`relative pl-3 text-lg font-bold tracking-tight text-white before:absolute before:left-0 before:top-1/2 before:h-4 before:w-1 before:-translate-y-1/2 before:rounded ${accentClass[accent] || accentClass.red}`}
          >
            {title}
          </h2>
          {subtitle ? <p className="mt-1 text-[12px] text-white/50">{subtitle}</p> : null}
        </div>
        <div className="hidden text-[11px] text-white/40 md:block">
          {videos.length} {videos.length === 1 ? 'asset' : 'assets'}
        </div>
      </div>
      <div className="rail-scroll">
        {videos.map((v) => (
          <VideoCard key={String(v.id)} video={v} />
        ))}
      </div>
    </section>
  );
}
