import { formatDuration } from '@/lib/format';
import type { VideoScene } from '@/lib/types';

interface SceneListProps {
  scenes: VideoScene[] | undefined;
  onSeek?: (seconds: number) => void;
}

export default function SceneList({ scenes, onSeek }: SceneListProps) {
  return (
    <section>
      <h2 className="text-sm font-semibold">Scenes</h2>
      {scenes?.length ? (
        <ol className="mt-2 max-h-56 space-y-1 overflow-y-auto">
          {scenes.map((scene, index) => {
            const range = `${formatDuration(scene.start_time_seconds)} – ${formatDuration(scene.end_time_seconds)}`;
            return (
              <li key={scene.id} className="flex flex-wrap items-baseline gap-x-3 rounded bg-white/5 px-3 py-2 text-sm">
                {onSeek ? (
                  <button type="button" onClick={() => onSeek(scene.start_time_seconds)}
                    aria-label={`Play scene ${index + 1} at ${formatDuration(scene.start_time_seconds)}`}
                    className="font-mono text-white underline underline-offset-4 hover:text-white/75">
                    {range}
                  </button>
                ) : <span className="font-mono text-white/70">{range}</span>}
                <span className="break-words text-white/75">{scene.summary || `Scene ${index + 1}`}</span>
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="mt-2 text-sm text-white/65">
          {scenes === undefined ? 'Could not load scenes.' : 'No scenes available for this video.'}
        </p>
      )}
    </section>
  );
}
