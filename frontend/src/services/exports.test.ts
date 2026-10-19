import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createExport, getExport, listExportPresets, listProjectExports } from './exports';

const PRESET = {
  key: 'youtube',
  label: 'YouTube',
  description: 'H.264 1080p',
  container: 'mp4',
  video_codec: 'h264' as const,
  audio_codec: 'aac',
  crf: 20,
  encoder_preset: 'medium',
  max_width: 1920,
  audio_bitrate: '192k',
};

const EXPORT = {
  id: 5,
  clip_id: 1,
  project_id: 'p'.repeat(32),
  preset: 'youtube',
  container: 'mp4',
  video_codec: 'h264' as const,
  audio_codec: 'aac',
  settings: { crf: 20 },
  editing_profile: 'clean',
  plan_snapshot: null,
  app_version: '0.1.0',
  status: 'ready' as const,
  file_size_bytes: 1024,
  error: null,
  file_url: '/api/exports/5/file',
  created_at: '2026-10-14T10:05:00',
  updated_at: '2026-10-14T10:05:00',
};

const BASE = 'http://127.0.0.1:8790/api';

describe('exports service', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('listExportPresets fetches the catalog', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => [PRESET] });

    const presets = await listExportPresets();

    expect(presets).toEqual([PRESET]);
    expect(fetchMock).toHaveBeenCalledWith(`${BASE}/export-presets`, expect.anything());
  });

  it('createExport posts the preset', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({ job_id: 30, export_id: 5, status: 'pending' }),
    });

    const result = await createExport(1, 'tiktok');

    expect(result.export_id).toBe(5);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${BASE}/clips/1/export`);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({ preset: 'tiktok' });
  });

  it('getExport fetches one export', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => EXPORT });

    const exportRow = await getExport(5);

    expect(exportRow.file_url).toBe('/api/exports/5/file');
    expect(fetchMock).toHaveBeenCalledWith(`${BASE}/exports/5`, expect.anything());
  });

  it('listProjectExports fetches project exports', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => [EXPORT] });

    await listProjectExports('p'.repeat(32));

    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/projects/${'p'.repeat(32)}/exports`,
      expect.anything(),
    );
  });

  it('surfaces export errors', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ detail: 'Clip has not been rendered yet' }),
    });

    await expect(createExport(1, 'youtube')).rejects.toThrow('has not been rendered');
  });
});
