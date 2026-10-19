/** Export contract types (mirror of backend Pydantic schemas). */

export type ExportStatus = 'pending' | 'processing' | 'ready' | 'failed';

export type ExportVideoCodec = 'h264' | 'h265';

/** A selectable export preset (roadmap Phase 18; guide §24). */
export interface ExportPreset {
  key: string;
  label: string;
  description: string;
  container: string;
  video_codec: ExportVideoCodec;
  audio_codec: string;
  crf: number;
  encoder_preset: string;
  max_width: number | null;
  audio_bitrate: string;
}

/** An export request and the state of its rendered file. */
export interface Export {
  id: number;
  clip_id: number;
  project_id: string;
  preset: string;
  container: string;
  video_codec: ExportVideoCodec;
  audio_codec: string;
  settings: Record<string, unknown> | null;
  editing_profile: string | null;
  plan_snapshot: Record<string, unknown> | null;
  app_version: string | null;
  status: ExportStatus;
  file_size_bytes: number | null;
  error: string | null;
  file_url: string | null;
  created_at: string;
  updated_at: string;
}
