import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload as UploadIcon } from 'lucide-react';
import { Dropzone } from '@/components/forms/Dropzone';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { useUploadVideo } from '@/state/hooks/useUploadVideo';
import { useVideos } from '@/state/hooks/useVideos';
import { MediaCard } from '@/components/media/MediaCard';
import { humanizeBytes } from '@/lib/format';
import { toast } from '@/components/ui/toastStore';

const ACCEPT = ['video/mp4', 'video/quicktime', 'video/x-matroska'];
const MAX_BYTES = 512 * 1024 * 1024;

export default function UploadPage(): JSX.Element {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [progress, setProgress] = useState(0);
  const upload = useUploadVideo();
  const videosQ = useVideos();

  const recent = useMemo(() => {
    const list = videosQ.data ?? [];
    return [...list].sort((a, b) => (a.created_at < b.created_at ? 1 : -1)).slice(0, 10);
  }, [videosQ.data]);

  useEffect(() => {
    if (!upload.isPending) setProgress(0);
  }, [upload.isPending]);

  const onSubmit = async () => {
    if (!file) return;
    setProgress(0);
    try {
      const result = await upload.mutateAsync({
        file,
        title: title.trim() || undefined,
        onProgress: setProgress,
      });
      toast.success('Upload complete', `Job #${result.job_id} created`);
      navigate(`/jobs/${result.job_id}`);
    } catch {
      // axios interceptor already toasted
    }
  };

  return (
    <div className="mx-auto max-w-rail px-4 pb-16 pt-8 sm:px-6 lg:px-12">
      <header className="mb-8 max-w-3xl">
        <h1 className="font-display text-3xl font-bold tracking-tightest text-text-0 sm:text-4xl">
          Upload a video
        </h1>
        <p className="mt-1 text-sm text-text-1">
          We'll probe metadata, sample frames, transcribe audio, segment scenes, and generate AI tags. You can review them after.
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-[2fr_1fr]">
        <section className="rounded-xl border border-bg-3 bg-bg-1 p-6">
          <Dropzone
            accept={ACCEPT}
            maxSizeBytes={MAX_BYTES}
            file={file}
            onChange={setFile}
            disabled={upload.isPending}
          />

          <div className="mt-5">
            <label htmlFor="title" className="mb-1 block text-xs font-medium text-text-1">
              Title <span className="text-text-2">(optional)</span>
            </label>
            <input
              id="title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Product demo — Q3"
              maxLength={255}
              disabled={upload.isPending}
              className="w-full rounded-md border border-bg-3 bg-bg-2 px-3 py-2 text-sm text-text-0 placeholder:text-text-2 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-60"
            />
          </div>

          {upload.isPending && (
            <div className="mt-5">
              <div className="flex items-center justify-between text-xs text-text-1">
                <span>Uploading…</span>
                <span>{progress}%</span>
              </div>
              <div
                className="mt-1 h-2 overflow-hidden rounded-full bg-bg-3"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={progress}
              >
                <div className="h-full bg-accent transition-all" style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}

          <div className="mt-6 flex items-center gap-3">
            <Button
              variant="primary"
              size="lg"
              onClick={onSubmit}
              disabled={!file}
              loading={upload.isPending}
              iconLeft={!upload.isPending ? <UploadIcon className="h-4 w-4" aria-hidden /> : undefined}
            >
              {upload.isPending ? 'Uploading' : 'Start processing'}
            </Button>
            {file && !upload.isPending && (
              <span className="text-xs text-text-2">{humanizeBytes(file.size)}</span>
            )}
          </div>
        </section>

        <aside>
          <h2 className="mb-3 font-display text-base font-semibold tracking-tight text-text-0">
            Recent uploads
          </h2>
          {videosQ.isLoading ? (
            <div className="flex flex-col gap-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-[64px] w-full" />
              ))}
            </div>
          ) : recent.length === 0 ? (
            <div className="rounded-md border border-dashed border-bg-3 bg-bg-1 px-4 py-8 text-center text-xs text-text-2">
              Nothing uploaded yet.
            </div>
          ) : (
            <ul className="flex flex-col gap-3">
              {recent.map((v) => (
                <li key={v.id} className="flex items-center gap-3">
                  <MediaCard video={v} size="sm" className="!h-[60px] !w-[107px]" />
                  <div className="min-w-0 flex-1 text-xs text-text-1">
                    <p className="line-clamp-1 text-sm font-semibold text-text-0">
                      {v.title ?? v.original_filename}
                    </p>
                    <p className="line-clamp-1 text-text-2">{humanizeBytes(v.file_size_bytes ?? null)}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </aside>
      </div>
    </div>
  );
}
