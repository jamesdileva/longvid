import type { Candidate, CandidateStatus } from '../types/candidate';
import { apiRequest } from './http';

/** Queue candidate generation for a video. Returns immediately (202). */
export async function generateCandidates(videoId: number): Promise<{ job_id: number; status: string }> {
  return apiRequest(`/videos/${videoId}/generate-candidates`, { method: 'POST' });
}

/** Re-score existing candidates with current weights (202). */
export async function rescoreCandidates(videoId: number): Promise<{ job_id: number; status: string }> {
  return apiRequest(`/videos/${videoId}/rescore-candidates`, { method: 'POST' });
}

export async function listVideoCandidates(videoId: number): Promise<Candidate[]> {
  return apiRequest<Candidate[]>(`/videos/${videoId}/candidates`);
}

export async function listProjectCandidates(projectId: string): Promise<Candidate[]> {
  return apiRequest<Candidate[]>(`/projects/${projectId}/candidates`);
}

export async function updateCandidateStatus(
  candidateId: number,
  status: CandidateStatus,
): Promise<Candidate> {
  return apiRequest<Candidate>(`/candidates/${candidateId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}
