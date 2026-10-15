import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getTranscript } from './transcripts';

const TRANSCRIPT = {
  id: 1,
  video_id: 7,
  language: null,
  duration_seconds: 12,
  created_at: '2026-10-13T14:05:00',
  segments: [],
};

const BASE = 'http://127.0.0.1:8790/api';

describe('transcripts service', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('fetches the video transcript', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => TRANSCRIPT });

    const transcript = await getTranscript(7);

    expect(transcript).toEqual(TRANSCRIPT);
    expect(fetchMock).toHaveBeenCalledWith(`${BASE}/videos/7/transcript`, expect.anything());
  });

  it('propagates the 404 when no transcript exists', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'No transcript yet' }),
    });

    await expect(getTranscript(7)).rejects.toThrow('No transcript yet');
  });
});
