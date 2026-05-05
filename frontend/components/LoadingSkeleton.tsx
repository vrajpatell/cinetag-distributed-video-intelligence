export function VideoCardSkeleton() {
  return (
    <div className="w-[280px] shrink-0 overflow-hidden rounded-xl border border-cinetag-border/70 bg-cinetag-panel/60">
      <div className="skeleton aspect-video w-full" />
      <div className="space-y-2 p-3.5">
        <div className="skeleton h-3.5 w-3/4 rounded" />
        <div className="skeleton h-3 w-full rounded" />
        <div className="skeleton h-3 w-1/2 rounded" />
      </div>
    </div>
  );
}

export function VideoRailSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="rail-scroll">
      {Array.from({ length: count }).map((_, i) => (
        <VideoCardSkeleton key={i} />
      ))}
    </div>
  );
}

export function MetricSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="panel px-4 py-4">
          <div className="skeleton h-3 w-1/2 rounded" />
          <div className="skeleton mt-3 h-7 w-2/3 rounded" />
          <div className="skeleton mt-2 h-3 w-1/3 rounded" />
        </div>
      ))}
    </div>
  );
}

export default function LoadingSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton h-3 w-full rounded" />
      ))}
    </div>
  );
}
