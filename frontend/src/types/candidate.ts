/** Candidate contract types (mirror of backend Pydantic schemas). */

export type CandidateStatus = 'pending' | 'accepted' | 'rejected';

export interface Candidate {
  id: number;
  video_id: number;
  start_seconds: number;
  end_seconds: number;
  status: CandidateStatus;
  semantic_score: number;
  audio_score: number;
  visual_score: number;
  context_score: number;
  standalone_score: number;
  novelty_score: number;
  overall_score: number;
  category: string | null;
  reason: string | null;
  source: string;
  event_ids: string | null;
  created_at: string;
  updated_at: string;
}
