import type { Video } from '../types/video';
import { API_BASE_URL, API_ORIGIN } from './config';
import { apiRequest } from './http';

/** All videos of a project, newest first. */
export async function listVideos(projectId: string): Promise<Video[]> {
  return apiRequest<Video[]>(`/projects/${projectId}/videos`);
}

/** Import a local video file (path chosen via the Electron dialog). */
export async function importVideo(projectId: string, path: string): Promise<Video> {
  return apiRequest<Video>(`/projects/${projectId}/videos`, {
    method: 'POST',
    body: JSON.stringify({ path }),
  });
}

export async function deleteVideo(videoId: number): Promise<void> {
  await apiRequest<void>(`/videos/${videoId}`, { method: 'DELETE' });
}

/** Resolve a backend-relative asset path (e.g. /api/videos/1/thumbnail). */
export function assetUrl(path: string | null): string | null {
  return path ? `${API_ORIGIN}${path}` : null;
}

export { API_BASE_URL };
