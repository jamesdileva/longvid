import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  generateCandidates,
  listProjectCandidates,
  listVideoCandidates,
  rescoreCandidates,
  updateCandidateStatus,
} from './candidates';

const CANDIDATE = {
  id: 1,
  video_id: 7,
  start_seconds: 812.2,
  end_seconds: 851.8,
  status: 'pending' as const,
  semantic_score: 0.91,
  audio_score: 0.79,
  visual_score: 0.91,
  context_score: 0.83,
  standalone_score: 0.9,
  novelty_score: 1,
  overall_score: 0.86,
  category: 'reaction',
  reason: 'High-energy reaction followed by a win',
  source: 'fake',
  event_ids: '3,7',
  created_at: '2026-10-14T10:00:00',
  updated_at: '2026-10-14T10:00:00',
};

const BASE = 'http://127.0.0.1:8790/api';

describe('candidates service', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('generateCandidates posts to the generate endpoint', async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 202, json: async () => ({ job_id: 5, status: 'queued' }) });

    const result = await generateCandidates(7);

    expect(result.job_id).toBe(5);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${BASE}/videos/7/generate-candidates`);
    expect(init.method).toBe('POST');
  });

  it('rescoreCandidates posts to the rescore endpoint', async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 202, json: async () => ({ job_id: 6, status: 'queued' }) });

    await rescoreCandidates(7);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${BASE}/videos/7/rescore-candidates`);
    expect(init.method).toBe('POST');
  });

  it('listVideoCandidates fetches video candidates', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => [CANDIDATE] });

    const candidates = await listVideoCandidates(7);

    expect(candidates).toEqual([CANDIDATE]);
    expect(fetchMock).toHaveBeenCalledWith(`${BASE}/videos/7/candidates`, expect.anything());
  });

  it('listProjectCandidates fetches project candidates', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => [CANDIDATE] });

    await listProjectCandidates('p'.repeat(32));

    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/projects/${'p'.repeat(32)}/candidates`,
      expect.anything(),
    );
  });

  it('updateCandidateStatus patches the status', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ ...CANDIDATE, status: 'accepted' }) });

    const updated = await updateCandidateStatus(1, 'accepted');

    expect(updated.status).toBe('accepted');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${BASE}/candidates/1`);
    expect(init.method).toBe('PATCH');
    expect(JSON.parse(init.body)).toEqual({ status: 'accepted' });
  });

  it('surfaces conflicts from duplicate generation', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ detail: 'Candidate generation is already active' }),
    });

    await expect(generateCandidates(7)).rejects.toThrow('already active');
  });
});
