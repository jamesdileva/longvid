import type { Project, ProjectCreate, ProjectUpdate } from '../types/project';
import { apiRequest } from './http';

/** Every project, newest first. */
export async function listProjects(): Promise<Project[]> {
  return apiRequest<Project[]>('/projects');
}

/** One project by id. Rejects with HTTP 404 detail when missing. */
export async function getProject(id: string): Promise<Project> {
  return apiRequest<Project>(`/projects/${id}`);
}

export async function createProject(payload: ProjectCreate): Promise<Project> {
  return apiRequest<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateProject(id: string, payload: ProjectUpdate): Promise<Project> {
  return apiRequest<Project>(`/projects/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deleteProject(id: string): Promise<void> {
  await apiRequest<void>(`/projects/${id}`, { method: 'DELETE' });
}
