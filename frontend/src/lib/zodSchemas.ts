import { z } from 'zod';

const isoDateOrNull = z
  .union([z.string(), z.null()])
  .optional()
  .transform((v) => v ?? null);

const isoDate = z.string();

export const VideoAssetSchema = z.object({
  id: z.number().int(),
  title: z.string().nullable().optional(),
  original_filename: z.string(),
  storage_key: z.string(),
  status: z.string(),
  duration_seconds: z.number().nullable().optional(),
  width: z.number().int().nullable().optional(),
  height: z.number().int().nullable().optional(),
  codec: z.string().nullable().optional(),
  bitrate: z.number().int().nullable().optional(),
  frame_rate: z.number().nullable().optional(),
  file_size_bytes: z.number().int().nullable().optional(),
  created_at: isoDate,
  updated_at: isoDate,
});

export type VideoAsset = z.infer<typeof VideoAssetSchema>;

export const ProcessingJobSchema = z.object({
  id: z.number().int(),
  video_id: z.number().int(),
  status: z.string(),
  current_stage: z.string().nullable().optional(),
  error_message: z.string().nullable().optional(),
  retry_count: z.number().int(),
  started_at: isoDateOrNull,
  completed_at: isoDateOrNull,
  created_at: isoDate,
  updated_at: isoDate,
});

export type ProcessingJob = z.infer<typeof ProcessingJobSchema>;

export const ProcessingStageRunSchema = z.object({
  id: z.number().int(),
  job_id: z.number().int(),
  stage_name: z.string(),
  status: z.string(),
  started_at: isoDateOrNull,
  completed_at: isoDateOrNull,
  duration_ms: z.number().int().nullable().optional(),
  error_message: z.string().nullable().optional(),
});

export type ProcessingStageRun = z.infer<typeof ProcessingStageRunSchema>;

export const FrameSampleSchema = z.object({
  id: z.number().int(),
  video_id: z.number().int(),
  timestamp_seconds: z.number(),
  storage_key: z.string(),
  description: z.string().nullable().optional(),
  created_at: isoDate,
});

export type FrameSample = z.infer<typeof FrameSampleSchema>;

export const SceneSegmentSchema = z.object({
  id: z.number().int(),
  video_id: z.number().int(),
  start_time_seconds: z.number(),
  end_time_seconds: z.number(),
  summary: z.string().nullable().optional(),
  created_at: isoDate,
});

export type SceneSegment = z.infer<typeof SceneSegmentSchema>;

export const TranscriptSchema = z
  .object({
    id: z.number().int(),
    video_id: z.number().int(),
    text: z.string(),
    language: z.string().nullable().optional(),
    confidence: z.number().nullable().optional(),
    created_at: isoDate,
  })
  .nullable();

export type Transcript = z.infer<typeof TranscriptSchema>;

export const GeneratedTagSchema = z.object({
  id: z.number().int(),
  video_id: z.number().int(),
  tag_type: z.string(),
  tag_value: z.string(),
  confidence: z.number().nullable().optional(),
  source: z.string(),
  status: z.string(),
  rationale: z.string().nullable().optional(),
  created_at: isoDate,
  updated_at: isoDate,
});

export type GeneratedTag = z.infer<typeof GeneratedTagSchema>;

export const SearchResultSchema = z.object({
  video_id: z.number().int(),
  title: z.string().nullable().optional(),
  score: z.number(),
  explanation: z.string(),
});

export type SearchResult = z.infer<typeof SearchResultSchema>;

export const UploadResponseSchema = z.object({
  video_id: z.number().int(),
  job_id: z.number().int(),
});

export type UploadResponse = z.infer<typeof UploadResponseSchema>;

export const RetryResponseSchema = z.object({
  status: z.string(),
});

export type RetryResponse = z.infer<typeof RetryResponseSchema>;

export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';

export type TagStatus = 'pending_review' | 'approved' | 'rejected';
