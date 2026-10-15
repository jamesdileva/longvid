import type { Transcript } from '../types/transcript';
import { apiRequest } from './http';

/** The transcript for a video. Rejects when none exists yet (404). */
export async function getTranscript(videoId: number): Promise<Transcript> {
  return apiRequest<Transcript>(`/videos/${videoId}/transcript`);
}
