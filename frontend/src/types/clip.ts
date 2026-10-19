/** Clip contract types (mirror of backend Pydantic schemas). */

export type ClipStatus = 'pending' | 'generating' | 'ready' | 'failed';

export type ClipSelection = 'top5' | 'top10' | 'all' | 'accepted';

/** Automatic trim decisions recorded by the backend (roadmap 10.2). */
export interface EditingPlanTrim {
  applied: boolean;
  original_start: number;
  original_end: number;
  sentence_start: boolean;
  sentence_end: boolean;
  silence_removed_seconds: number;
}

/** Resolved audio processing recorded by the backend (roadmap 10.4). */
export interface EditingPlanAudio {
  loudness_target_lufs: number;
  true_peak_db: number;
  loudness_range: number;
  gate_threshold_db: number;
  filter: string;
}

/** Resolved center-crop/scale conversion recorded by the backend (roadmap 11). */
export interface EditingPlanFraming {
  target_width: number;
  target_height: number;
  crop_width: number;
  crop_height: number;
  crop_x: number;
  crop_y: number;
  zoom: number;
  filter: string;
  dynamic?: boolean;
  keyframes?: number[][];
}

/** Pacing decision recorded by the backend (roadmap 12.1). */
export interface EditingPlanPacing {
  style: string;
  speech_ratio: number;
  silence_ratio: number;
  scene_changes_per_minute: number;
  dead_air_runs: number[][];
  silence_removed_seconds: number;
  applied: boolean;
  video_filter: string | null;
  audio_filter: string | null;
}

/** Deterministic editing plan recorded on a clip (guide §21). */
export interface EditingPlan {
  plan_version: number;
  profile: string;
  source: string;
  start: number;
  end: number;
  aspect_ratio: string;
  captions: boolean;
  zoom: boolean;
  audio_normalization: boolean;
  trim?: EditingPlanTrim;
  audio?: EditingPlanAudio;
  framing?: EditingPlanFraming;
  pacing?: EditingPlanPacing;
}

export interface Clip {
  id: number;
  video_id: number;
  candidate_id: number | null;
  title: string | null;
  start_seconds: number;
  end_seconds: number;
  duration_seconds: number;
  editing_profile: string;
  editing_plan: EditingPlan | null;
  status: ClipStatus;
  file_size_bytes: number | null;
  error: string | null;
  file_url: string | null;
  caption_srt_url: string | null;
  caption_ass_url: string | null;
  created_at: string;
  updated_at: string;
}
