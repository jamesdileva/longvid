import type { Export, ExportPreset } from '../types/export';
import { apiRequest } from './http';

export interface CreateExportResult {
  job_id: number;
  export_id: number;
  status: string;
}

export async function listExportPresets(): Promise<ExportPreset[]> {
  return apiRequest<ExportPreset[]>('/export-presets');
}

/** Queue an export of a ready clip through a delivery preset (202). */
export async function createExport(
  clipId: number,
  preset: string,
): Promise<CreateExportResult> {
  return apiRequest<CreateExportResult>(`/clips/${clipId}/export`, {
    method: 'POST',
    body: JSON.stringify({ preset }),
  });
}

export async function getExport(exportId: number): Promise<Export> {
  return apiRequest<Export>(`/exports/${exportId}`);
}

export async function listProjectExports(projectId: string): Promise<Export[]> {
  return apiRequest<Export[]>(`/projects/${projectId}/exports`);
}
