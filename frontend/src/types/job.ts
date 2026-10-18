/** Job contract types (mirror of backend Pydantic schemas). */

/**
 * Known job types. Additional stages appear here as they are implemented
 * (transcribe, detect_scenes, analyze_events, ...).
 */
export type JobType =
  | 'extract_audio'
  | 'transcribe'
  | 'detect_scenes'
  | 'analyze_events'
  | 'track_subjects'
  | 'generate_candidates'
  | 'score_candidates'
  | 'generate_clip'
  | 'export';

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface Job {
  id: number;
  video_id: number;
  type: JobType;
  status: JobStatus;
  progress: number;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export const ACTIVE_JOB_STATUSES: JobStatus[] = ['queued', 'running'];

export function isActiveJob(job: Job): boolean {
  return ACTIVE_JOB_STATUSES.includes(job.status);
}
