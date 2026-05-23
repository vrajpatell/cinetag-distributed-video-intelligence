'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ApiError, publishVideo } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export default function PublishVideoButton({
  videoId,
  initialStatus,
}: {
  videoId: number | string;
  initialStatus?: string;
}) {
  const [status, setStatus] = useState<string | undefined>(initialStatus);

  const publishMutation = useMutation({
    mutationFn: () => publishVideo(videoId),
    onSuccess: (updated) => {
      setStatus(String(updated.status || 'published'));
      toast.success('Video published successfully');
    },
    onError: (err: Error) => {
      const msg =
        err instanceof ApiError
          ? err.detail || err.message
          : err instanceof Error
            ? err.message
            : 'Publish failed';
      toast.error('Publish failed', { description: msg });
    },
  });

  if (status === 'published') {
    return (
      <Badge variant="emerald" className="!text-[10.5px] uppercase tracking-wider">
        published
      </Badge>
    );
  }

  const canPublish = status === 'review_ready';

  return (
    <div className="space-y-2">
      <Button
        type="button"
        variant="success"
        size="sm"
        disabled={!canPublish || publishMutation.isPending}
        onClick={() => publishMutation.mutate()}
        className="!text-xs"
      >
        {publishMutation.isPending ? 'Publishing…' : 'Publish video'}
      </Button>
      {!canPublish && status !== 'published' ? (
        <p className="text-[11px] text-white/55">
          Resolve all pending tag reviews before publishing.
        </p>
      ) : null}
    </div>
  );
}
