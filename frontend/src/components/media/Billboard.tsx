import { useNavigate } from 'react-router-dom';
import { Info, Play } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/Button';
import { humanizeBytes, humanizeDuration } from '@/lib/format';
import type { VideoAsset } from '@/lib/zodSchemas';

export interface BillboardProps {
  video: VideoAsset;
  overview?: string | null;
}

const GRADIENTS = [
  'radial-gradient(ellipse at 70% 30%, #4a0a0c 0%, #0b0b0f 60%, #000 100%)',
  'radial-gradient(ellipse at 75% 35%, #1f3a8a 0%, #0b0b0f 60%, #000 100%)',
  'radial-gradient(ellipse at 65% 25%, #831010 0%, #0b0b0f 55%, #000 100%)',
  'radial-gradient(ellipse at 80% 30%, #3f4a1f 0%, #0b0b0f 60%, #000 100%)',
];

export function Billboard({ video, overview }: BillboardProps): JSX.Element {
  const navigate = useNavigate();
  const seed = video.id + (video.title ?? video.original_filename);
  const idx = Math.abs(hash(seed)) % GRADIENTS.length;
  const summary =
    (overview ?? '').trim().length > 0
      ? (overview as string)
      : `${video.original_filename} — uploaded asset awaiting analysis.`;
  const goDetail = () => navigate(`/videos/${video.id}`);

  return (
    <section
      role="region"
      aria-label="Featured video"
      className="relative isolate min-h-[520px] overflow-hidden"
      style={{ height: '80vh' }}
    >
      <div aria-hidden className="absolute inset-0" style={{ backgroundImage: GRADIENTS[idx] }} />
      <div aria-hidden className="absolute inset-0 bg-fade-right" />
      <div aria-hidden className="absolute inset-x-0 bottom-0 h-2/3 bg-fade-bottom" />

      <div className="relative z-10 mx-auto flex h-full max-w-rail flex-col justify-end gap-4 px-4 pb-16 sm:px-6 sm:pb-20 lg:px-12 lg:pb-24">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <p className="mb-2 text-xs font-bold uppercase tracking-[0.3em] text-accent">Featured · most recent</p>
          <h1
            className="font-display font-black tracking-tightest text-text-0 drop-shadow"
            style={{ fontSize: 'clamp(2.5rem, 6vw, 5.5rem)', lineHeight: 1.02 }}
          >
            {video.title ?? video.original_filename}
          </h1>
          <p className="mt-4 max-w-[36ch] text-sm text-text-1 sm:text-base">{truncateText(summary, 240)}</p>

          <dl className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-text-1">
            <Meta label="Duration">{humanizeDuration(video.duration_seconds ?? null)}</Meta>
            {video.codec && <Meta label="Codec">{video.codec}</Meta>}
            {video.width && video.height && (
              <Meta label="Resolution">
                {video.width}×{video.height}
              </Meta>
            )}
            <Meta label="Size">{humanizeBytes(video.file_size_bytes ?? null)}</Meta>
            <Meta label="Status">
              <span className="capitalize">{video.status}</span>
            </Meta>
          </dl>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Button size="lg" onClick={goDetail} iconLeft={<Play className="h-5 w-5" aria-hidden />}>
              Play
            </Button>
            <Button
              variant="secondary"
              size="lg"
              onClick={goDetail}
              iconLeft={<Info className="h-5 w-5" aria-hidden />}
            >
              More info
            </Button>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function Meta({ label, children }: { label: string; children: React.ReactNode }): JSX.Element {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="text-text-2">{label}</span>
      <span className="text-text-0">{children}</span>
    </span>
  );
}

function truncateText(s: string, max: number): string {
  if (s.length <= max) return s;
  return `${s.slice(0, max - 1).trimEnd()}…`;
}

function hash(input: string | number): number {
  const s = String(input);
  let h = 0;
  for (let i = 0; i < s.length; i += 1) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  return h;
}
