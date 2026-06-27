// =====================================================
// AGC AI Highlight Creator
// frontend/types/pipeline.ts
// Production Types
// AGC-024
// =====================================================

export type JobStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed";

export interface UploadResponse {
  success: boolean;
  message: string;
  filename: string;
  original_filename: string;
  size_mb: number;
  location: string;
}

export interface PipelineStartResponse {
  success: boolean;
  job_id: string;
  message: string;
}

export interface Highlight {
  timestamp: number;
  duration: number;
  score: number;
  label?: string;
}

export interface PipelineResult {
  reel_path?: string;
  vertical_path?: string;
  metadata_path?: string;
  result_path?: string;
  highlights?: Highlight[];
}

export interface SocialExport {
  description?: string;
  caption?: string;
}

export interface SocialExports {
  youtube?: SocialExport;
  instagram?: SocialExport;
  tiktok?: SocialExport;
}

export interface ProcessingStats {
  video_duration?: number;
  frames_analyzed?: number;
  highlights_found?: number;
  processing_time?: number;
}

export interface HighlightItem {
  timestamp: number;
  duration?: number;
  score: number;
  label?: string;
  action?: string;
  clip_path?: string;
}

export interface ExtendedPipelineResult {
  final_reel?: string;
  vertical_reel?: string;
  thumbnail?: string;
  result_json?: string;
  title?: string;
  description?: string;
  hashtags?: string[];
  highlights_found?: number;
  stats?: ProcessingStats;
  social_exports?: SocialExports;
  all_highlights?: HighlightItem[];
}

export interface PipelineJob {
  job_id: string;
  status: JobStatus;
  progress: number;
  created_at?: string;
  updated_at?: string;
  error?: string | null;
  result?: ExtendedPipelineResult | null;
}

export interface JobResponse {
  success: boolean;
  data: PipelineJob;
}

export interface JobsResponse {
  success: boolean;
  count: number;
  data: PipelineJob[];
}

export interface JobStats {
  queued: number;
  running: number;
  completed: number;
  failed: number;
}

export interface JobStatsResponse {
  success: boolean;
  data: JobStats;
}

export interface ProgressData {
  progress: number;
  current_step?: string;
}

export interface ProgressResponse {
  success: boolean;
  data: ProgressData;
}

export interface HistoryItem {
  video_name: string;
  date: string;
  reel_path: string;
  highlights_count: number;
}

export interface HistoryResponse {
  success: boolean;
  data: HistoryItem[];
}