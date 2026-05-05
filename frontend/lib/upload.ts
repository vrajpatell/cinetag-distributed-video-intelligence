import { ApiError, completeUpload, initUpload } from './api';

export type UploadStage =
  | 'preparing_signed_upload'
  | 'uploading_to_cloud_storage'
  | 'finalizing_upload'
  | 'creating_processing_job'
  | 'queued_for_analysis'
  | 'failed';

export interface UploadProgressInfo {
  percent: number;
  bytesUploaded: number;
  bytesTotal: number;
  speedBytesPerSec: number;
  etaSeconds: number;
}

export interface UploadResult {
  video_id: number;
  job_id: number;
  storage_key: string;
  status: string;
}

export interface UploadOptions {
  file: File;
  title?: string;
  onStageChange?: (stage: UploadStage) => void;
  onProgress?: (info: UploadProgressInfo) => void;
  signal?: AbortSignal;
}

export class UploadError extends Error {
  stage: UploadStage;
  endpoint?: string;
  status?: number;
  hint?: string;
  constructor(
    message: string,
    opts: { stage: UploadStage; endpoint?: string; status?: number; hint?: string }
  ) {
    super(message);
    this.name = 'UploadError';
    this.stage = opts.stage;
    this.endpoint = opts.endpoint;
    this.status = opts.status;
    this.hint = opts.hint;
  }
}

export async function uploadVideoDirectToGcs(
  options: UploadOptions
): Promise<UploadResult> {
  const { file, title, onStageChange, onProgress, signal } = options;

  onStageChange?.('preparing_signed_upload');
  let init;
  try {
    init = await initUpload({
      filename: file.name,
      content_type: file.type || 'application/octet-stream',
      size_bytes: file.size,
      title,
    });
  } catch (err) {
    onStageChange?.('failed');
    if (err instanceof ApiError) {
      throw new UploadError('Could not prepare upload', {
        stage: 'preparing_signed_upload',
        endpoint: err.endpoint,
        status: err.status,
        hint: err.detail,
      });
    }
    throw new UploadError('Could not prepare upload', { stage: 'preparing_signed_upload' });
  }

  onStageChange?.('uploading_to_cloud_storage');
  await putToSignedUrl({
    url: init.upload_url,
    file,
    headers: init.required_headers,
    signal,
    onProgress,
  });

  onStageChange?.('finalizing_upload');
  let complete;
  try {
    onStageChange?.('creating_processing_job');
    complete = await completeUpload({
      video_id: init.video_id,
      storage_key: init.storage_key,
      title,
    });
  } catch (err) {
    onStageChange?.('failed');
    if (err instanceof ApiError) {
      throw new UploadError('Video uploaded, but processing job could not be created', {
        stage: 'creating_processing_job',
        endpoint: err.endpoint,
        status: err.status,
        hint: err.detail,
      });
    }
    throw new UploadError('Video uploaded, but processing job could not be created', {
      stage: 'creating_processing_job',
    });
  }

  onStageChange?.('queued_for_analysis');
  return {
    video_id: complete.video_id,
    job_id: complete.job_id,
    storage_key: init.storage_key,
    status: complete.status ?? 'queued',
  };
}

function putToSignedUrl(params: {
  url: string;
  file: File;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  onProgress?: (info: UploadProgressInfo) => void;
}): Promise<void> {
  const { url, file, headers, signal, onProgress } = params;
  return new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', url, true);
    if (headers) {
      for (const [k, v] of Object.entries(headers)) {
        try {
          xhr.setRequestHeader(k, v);
        } catch {
          /* ignored */
        }
      }
    } else if (file.type) {
      xhr.setRequestHeader('Content-Type', file.type);
    }
    const started = Date.now();
    xhr.upload.onprogress = (e) => {
      if (!onProgress) return;
      if (!e.lengthComputable) return;
      const elapsed = Math.max((Date.now() - started) / 1000, 0.001);
      const speed = e.loaded / elapsed;
      const remaining = e.total - e.loaded;
      onProgress({
        percent: (e.loaded / e.total) * 100,
        bytesUploaded: e.loaded,
        bytesTotal: e.total,
        speedBytesPerSec: speed,
        etaSeconds: speed > 0 ? remaining / speed : 0,
      });
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        reject(
          new UploadError(`Cloud Storage rejected upload (${xhr.status})`, {
            stage: 'uploading_to_cloud_storage',
            status: xhr.status,
            endpoint: url,
            hint: xhr.responseText?.slice(0, 200),
          })
        );
      }
    };
    xhr.onerror = () =>
      reject(
        new UploadError('Could not upload video to Cloud Storage', {
          stage: 'uploading_to_cloud_storage',
          endpoint: url,
          hint: 'Check CORS configuration on your GCS bucket.',
        })
      );
    xhr.ontimeout = () =>
      reject(
        new UploadError('Upload timed out', {
          stage: 'uploading_to_cloud_storage',
          endpoint: url,
        })
      );
    if (signal) {
      const onAbort = () => {
        try {
          xhr.abort();
        } catch {
          /* ignored */
        }
        reject(
          new UploadError('Upload cancelled', {
            stage: 'uploading_to_cloud_storage',
            endpoint: url,
          })
        );
      };
      if (signal.aborted) onAbort();
      else signal.addEventListener('abort', onAbort, { once: true });
    }
    xhr.send(file);
  });
}

export const STAGE_LABELS: Record<UploadStage, string> = {
  preparing_signed_upload: 'Preparing signed upload',
  uploading_to_cloud_storage: 'Uploading to Cloud Storage',
  finalizing_upload: 'Finalizing upload',
  creating_processing_job: 'Creating processing job',
  queued_for_analysis: 'Queued for analysis',
  failed: 'Upload failed',
};
