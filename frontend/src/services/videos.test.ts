import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { assetUrl, deleteVideo, importVideo, listVideos } from './videos';

const VIDEO = {
  id: 1,
  project_id: 'a'.repeat(32),
  filename: 'clip.mp4',
  status: 'ready' as const,
  duration_seconds: 12.5,
  width: 1920,
  height: 1080,
  fps: 30,
  video_codec: 'h264',
  audio_codec: 'aac',
  sample_rate: 48000,
  channels: 2,
  file_size_bytes: 1024,
  thumbnail_url: '/api/videos/1/thumbnail',
  preview_url: '/api/videos/1/preview',
  created_at: '2026-10-13T14:00:00',
  updated_at: '2026-10-13T14:00:00',
};

const BASE = 'http://127.0.0.1:8790/api';

describe('videos service', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('listVideos calls the project videos endpoint', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => [VIDEO] });

    const videos = await listVideos('p'.repeat(32));

    expect(videos).toEqual([VIDEO]);
    expect(fetchMock).toHaveBeenCalledWith(`${BASE}/projects/${'p'.repeat(32)}/videos`, expect.anything());
  });

  it('importVideo posts the file path', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => VIDEO });

    await importVideo('p'.repeat(32), 'D:/clips/clip.mp4');

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${BASE}/projects/${'p'.repeat(32)}/videos`);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({ path: 'D:/clips/clip.mp4' });
  });

  it('deleteVideo resolves on 204', async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 204, json: async () => ({}) });

    await expect(deleteVideo(1)).resolves.toBeUndefined();

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${BASE}/videos/1`);
    expect(init.method).toBe('DELETE');
  });

  it('surfaces import errors from the backend', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Unsupported file type. Allowed: ...' }),
    });

    await expect(importVideo('p'.repeat(32), 'x.txt')).rejects.toThrow('Unsupported file type');
  });
});

describe('assetUrl', () => {
  it('resolves backend-relative paths against the API origin', () => {
    expect(assetUrl('/api/videos/1/thumbnail')).toBe('http://127.0.0.1:8790/api/videos/1/thumbnail');
  });

  it('returns null for missing assets', () => {
    expect(assetUrl(null)).toBeNull();
  });
});
