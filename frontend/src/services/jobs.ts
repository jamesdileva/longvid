import type { Job } from '../types/job';
import { apiRequest } from './http';

/** Queue a background job for a video. Returns the queued job immediately. */
export async function processVideo(videoId: number, type: string): Promise<Job> {
  return apiRequest<Job>(`/videos/${videoId}/process`, {
    method: 'POST',
    body: JSON.stringify({ type }),
  });
}

export async function listVideoJobs(videoId: number): Promise<Job[]> {
  return apiRequest<Job[]>(`/jobs/video/${videoId}`);
}

export async function cancelJob(jobId: number): Promise<Job> {
  return apiRequest<Job>(`/jobs/${jobId}/cancel`, { method: 'POST' });
}
