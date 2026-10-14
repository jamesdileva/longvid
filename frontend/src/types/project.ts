/** Project contract types (mirror of backend Pydantic schemas). */

export type ProjectStatus = 'active' | 'archived';

export interface Project {
  id: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  workspace_path: string;
  video_count: number;
  clip_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string | null;
}

export interface ProjectUpdate {
  name?: string;
  description?: string | null;
  status?: ProjectStatus;
}
