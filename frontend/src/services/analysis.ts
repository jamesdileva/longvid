import type { AnalysisEvent, Scene } from '../types/analysis';
import { apiRequest } from './http';

/** Detected scenes for a video, in order. */
export async function listScenes(videoId: number): Promise<Scene[]> {
  return apiRequest<Scene[]>(`/videos/${videoId}/scenes`);
}

/** Analysis events for a video, chronological. */
export async function listEvents(videoId: number): Promise<AnalysisEvent[]> {
  return apiRequest<AnalysisEvent[]>(`/videos/${videoId}/events`);
}
