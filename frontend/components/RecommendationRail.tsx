import type { VideoSummary } from '@/lib/types';
import VideoRail from './VideoRail';

export default function RecommendationRail({
  title = 'Because of these tags',
  reason,
  videos,
}: {
  title?: string;
  reason?: string;
  videos: VideoSummary[];
}) {
  return (
    <div className="space-y-2">
      {reason ? (
        <div className="mx-auto max-w-[1400px] px-5 text-[12px] text-cinetag-redGlow/80">
          <span className="text-white/55">Recommendation reason:</span> {reason}
        </div>
      ) : null}
      <VideoRail title={title} videos={videos} accent="violet" />
    </div>
  );
}
