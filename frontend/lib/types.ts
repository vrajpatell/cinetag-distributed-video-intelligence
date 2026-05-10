export type JobStatus =
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'partially_completed'
  | 'unknown';

export type ProcessingStage =
  | 'queued'
  | 'metadata_extraction'
  | 'frame_sampling'
  | 'scene_segmentation'
  | 'transcription'
  | 'llm_tagging'
  | 'embedding'
  | 'review_ready'
  | 'completed';

export type VideoStatus =
  | 'upload_pending'
  | 'uploaded'
  | 'processing'
  | 'review_ready'
  | 'published'
  | 'failed'
  | 'unknown';

export type TagType =
  | 'genre'
  | 'mood'
  | 'object'
  | 'scene'
  | 'theme'
  | 'moderation'
  | 'entity'
  | 'language';

export type TagSource = 'transcript' | 'visual_frame' | 'llm' | 'metadata' | 'manual';
export type TagReviewStatus = 'pending_review' | 'approved' | 'rejected';

export interface VideoSummary {
  id: number | string;
  title: string;
  description?: string;
  summary?: string;
  duration_seconds?: number;
  status?: VideoStatus | string;
  thumbnailKey?: string;
  thumbnailGradient?: string;
  tags?: { value: string; type: TagType; confidence?: number }[];
  genres?: string[];
  moods?: string[];
  confidence?: number;
  processingStage?: ProcessingStage | string;
  recommendationReason?: string;
  width?: number;
  height?: number;
  codec?: string;
  bitrate?: number;
  frame_rate?: number;
  file_size_bytes?: number;
  created_at?: string;
  updated_at?: string;
  storage_key?: string;
  isDemo?: boolean;
}

export interface JobSummary {
  id: number | string;
  video_id?: number | string;
  video_title?: string;
  status: JobStatus | string;
  current_stage?: ProcessingStage | string;
  retry_count?: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at?: string;
  updated_at?: string;
  stage_runs?: ProcessingStageRun[];
  isDemo?: boolean;
}

export interface ProcessingStageRun {
  id: number | string;
  job_id: number | string;
  stage_name: ProcessingStage | string;
  status: JobStatus | string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  error_message?: string;
}

export interface ReviewItem {
  id: number | string;
  video_id: number | string;
  video_title?: string;
  tag_type: TagType;
  tag_value: string;
  confidence: number;
  source: TagSource;
  status: TagReviewStatus;
  rationale?: string;
  transcript_snippet?: string;
  created_at?: string;
  isDemo?: boolean;
}

export interface SearchResult {
  video_id: number | string;
  title?: string;
  score: number;
  explanation?: string;
  matched_tags?: { value: string; type: TagType }[];
  thumbnailGradient?: string;
  duration_seconds?: number;
  genres?: string[];
  moods?: string[];
  status?: VideoStatus | string;
  isDemo?: boolean;
}

export interface VideoPlaybackResponse {
  url: string;
  content_type: string;
  expires_in_seconds: number;
  poster_url?: string | null;
  duration_seconds?: number | null;
  file_size_bytes?: number | null;
}

export interface PlatformMetric {
  label: string;
  value: string;
  trend?: string;
  hint?: string;
  accent?: 'red' | 'sky' | 'emerald' | 'amber' | 'violet' | 'rose';
}
