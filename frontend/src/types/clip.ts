/** Clip contract types (mirror of backend Pydantic schemas). */

export type ClipStatus = 'pending' | 'generating' | 'ready' | 'failed';

export type ClipSelection = 'top5' | 'top10' | 'all' | 'accepted';

export interface Clip {
  id: number;
  video_id: number;
  candidate_id: number | null;
  title: string | null;
  start_seconds: number;
  end_seconds: number;
  duration_seconds: number;
  editing_profile: string;
  status: ClipStatus;
  file_size_bytes: number | null;
  error: string | null;
  file_url: string | null;
  created_at: string;
  updated_at: string;
}
