/** Editing profile contract (mirror of backend EditingProfileRead, guide §16). */

export interface EditingProfile {
  key: string;
  label: string;
  description: string;
  aspect_ratio: string;
  captions: boolean;
  zoom: boolean;
  audio_normalization: boolean;
  max_duration_seconds: number | null;
}
