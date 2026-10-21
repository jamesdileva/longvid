import type { ContentProfile } from '../types/contentProfile';
import type { Video } from '../types/video';
import { apiRequest } from './http';

/** The content profiles available for highlight detection. */
export async function listContentProfiles(): Promise<ContentProfile[]> {
  return apiRequest<ContentProfile[]>('/content-profiles');
}

/** Select the content profile used when detecting a video's highlights. */
export async function updateContentProfile(
  videoId: number,
  contentProfile: string,
): Promise<Video> {
  return apiRequest<Video>(`/videos/${videoId}/content-profile`, {
    method: 'PUT',
    body: JSON.stringify({ content_profile: contentProfile }),
  });
}
