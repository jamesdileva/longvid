import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { deleteClip, generateClips, listProjectClips, listVideoClips, updateClip } from './clips';

const CLIP = {
  id: 1,
  video_id: 7,
  candidate_id: 3,
  title: 'Best play',
  start_seconds: 812.2,
  end_seconds: 851.8,
  duration_seconds: 39.6,
  editing_profile: 'clean',
  status: 'ready' as const,
  file_size_bytes: 5_242_880,
  error: null,
  file_url: '/api/clips/1/file',
  created_at: '2026-10-14T10:05:00',
  updated_at: '2026-10-14T10:05:00',
};

const BASE = 'http://127.0.0.1:8790/api';

describe('clips service', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('generateClips posts selection and returns the batch result', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({ job_id: 20, status: 'queued', clip_count: 2 }),
    });

    const result = await generateClips(7, { selection: 'top5' });

    expect(result.clip_count).toBe(2);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${BASE}/videos/7/generate-clips`);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({
      selection: 'top5',
      candidate_ids: null,
      editing_profile: 'clean',
    });
  });

  it('generateClips sends explicit candidate ids', async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 202, json: async () => ({}) });

    await generateClips(7, { selection: 'all', candidateIds: [3, 4], editingProfile: 'shorts' });

    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      selection: 'all',
      candidate_ids: [3, 4],
      editing_profile: 'shorts',
    });
  });

  it('listVideoClips fetches video clips', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => [CLIP] });

    const clips = await listVideoClips(7);

    expect(clips).toEqual([CLIP]);
    expect(fetchMock).toHaveBeenCalledWith(`${BASE}/videos/7/clips`, expect.anything());
  });

  it('listProjectClips fetches project clips', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => [CLIP] });

    await listProjectClips('p'.repeat(32));

    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/projects/${'p'.repeat(32)}/clips`,
      expect.anything(),
    );
  });

  it('updateClip patches the title', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ ...CLIP, title: 'Renamed' }) });

    const updated = await updateClip(1, 'Renamed');

    expect(updated.title).toBe('Renamed');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${BASE}/clips/1`);
    expect(init.method).toBe('PATCH');
    expect(JSON.parse(init.body)).toEqual({ title: 'Renamed' });
  });

  it('deleteClip issues a DELETE', async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 204, json: async () => undefined });

    await deleteClip(1);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${BASE}/clips/1`);
    expect(init.method).toBe('DELETE');
  });

  it('surfaces conflicts when no candidates exist', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ detail: 'No candidates; detect highlights first' }),
    });

    await expect(generateClips(7)).rejects.toThrow('detect highlights first');
  });
});
