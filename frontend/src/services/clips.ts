import type { Clip, ClipSelection } from '../types/clip';
import { apiRequest } from './http';

export interface GenerateClipsResult {
  job_id: number;
  status: string;
  clip_count: number;
}

export interface GenerateClipsOptions {
  selection?: ClipSelection;
  candidateIds?: number[];
  editingProfile?: string;
}

/** Create clip definitions for the chosen candidates and queue rendering (202). */
export async function generateClips(
  videoId: number,
  options: GenerateClipsOptions = {},
): Promise<GenerateClipsResult> {
  return apiRequest<GenerateClipsResult>(`/videos/${videoId}/generate-clips`, {
    method: 'POST',
    body: JSON.stringify({
      selection: options.selection ?? 'top5',
      candidate_ids: options.candidateIds ?? null,
      editing_profile: options.editingProfile ?? 'clean',
    }),
  });
}

export async function listVideoClips(videoId: number): Promise<Clip[]> {
  return apiRequest<Clip[]>(`/videos/${videoId}/clips`);
}

export async function listProjectClips(projectId: string): Promise<Clip[]> {
  return apiRequest<Clip[]>(`/projects/${projectId}/clips`);
}

export async function updateClip(clipId: number, title: string): Promise<Clip> {
  return apiRequest<Clip>(`/clips/${clipId}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  });
}

export async function deleteClip(clipId: number): Promise<void> {
  await apiRequest<void>(`/clips/${clipId}`, { method: 'DELETE' });
}
