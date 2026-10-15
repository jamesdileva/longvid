import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { listEvents, listScenes } from './analysis';

const SCENE = {
  id: 1,
  video_id: 7,
  position: 0,
  start_seconds: 0,
  end_seconds: 6.2,
  score: 0.42,
};

const EVENT = {
  id: 1,
  video_id: 7,
  type: 'scene_change',
  start_seconds: 6.2,
  end_seconds: 6.2,
  confidence: 0.42,
  source: 'scene_detection',
  payload: { score: 0.42 },
  created_at: '2026-10-13T15:00:00',
};

const BASE = 'http://127.0.0.1:8790/api';

describe('analysis service', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('listScenes fetches the scenes endpoint', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => [SCENE] });

    const scenes = await listScenes(7);

    expect(scenes).toEqual([SCENE]);
    expect(fetchMock).toHaveBeenCalledWith(`${BASE}/videos/7/scenes`, expect.anything());
  });

  it('listEvents fetches the events endpoint', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => [EVENT] });

    const events = await listEvents(7);

    expect(events).toEqual([EVENT]);
    expect(fetchMock).toHaveBeenCalledWith(`${BASE}/videos/7/events`, expect.anything());
  });

  it('surfaces 404 errors for unknown videos', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Video not found' }),
    });

    await expect(listScenes(999)).rejects.toThrow('Video not found');
  });
});
