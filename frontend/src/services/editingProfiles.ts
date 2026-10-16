import type { EditingProfile } from '../types/editingProfile';
import { apiRequest } from './http';

/** The named editing profiles (Clean / YouTube / Shorts / TikTok). */
export async function listEditingProfiles(): Promise<EditingProfile[]> {
  return apiRequest<EditingProfile[]>('/editing-profiles');
}
