/** Transcript contract types (mirror of backend Pydantic schemas). */

export interface TranscriptSegment {
  id: number;
  position: number;
  start_seconds: number;
  end_seconds: number;
  text: string;
  confidence: number | null;
}

export interface Transcript {
  id: number;
  video_id: number;
  language: string | null;
  duration_seconds: number | null;
  created_at: string;
  segments: TranscriptSegment[];
}
