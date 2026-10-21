/** Video contract types (mirror of backend Pydantic schemas). */

export type VideoStatus = 'pending' | 'ready' | 'failed';

export interface Video {
  id: number;
  project_id: string;
  filename: string;
  status: VideoStatus;
  duration_seconds: number | null;
  width: number | null;
  height: number | null;
  fps: number | null;
  video_codec: string | null;
  audio_codec: string | null;
  sample_rate: number | null;
  channels: number | null;
  file_size_bytes: number | null;
  audio_path: string | null;
  content_profile: string;
  thumbnail_url: string | null;
  preview_url: string | null;
  created_at: string;
  updated_at: string;
}
