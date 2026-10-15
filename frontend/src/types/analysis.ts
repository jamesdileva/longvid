/** Analysis contract types (mirror of backend Pydantic schemas). */

export interface Scene {
  id: number;
  video_id: number;
  position: number;
  start_seconds: number;
  end_seconds: number;
  score: number | null;
}

export interface AnalysisEvent {
  id: number;
  video_id: number;
  type: string;
  start_seconds: number;
  end_seconds: number;
  confidence: number | null;
  source: string;
  payload: Record<string, unknown> | null;
  created_at: string;
}

export const KNOWN_EVENT_TYPES = [
  'scene_change',
  'silence',
  'audio_spike',
  'speech_density',
  'reaction',
  'laughter',
  'joke',
  'surprise',
  'victory',
  'failure',
  'high_energy',
] as const;
