import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cancelJob, listVideoJobs, processVideo } from './jobs';

const JOB = {
  id: 5,
  video_id: 1,
  type: 'extract_audio' as const,
  status: 'completed' as const,
  progress: 1,
  error: null,
  started_at: '2026-10-13T14:01:00',
  completed_at: '2026-10-13T14:01:05',
  created_at: '2026-10-13T14:00:30',
  updated_at: '2026-10-13T14:01:05',
};

const BASE = 'http://127.0.0.1:8790/api';

describe('jobs service', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('processVideo posts the job type', async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 202, json: async () => ({ ...JOB, status: 'queued', progress: 0 }) });

    const job = await processVideo(7, 'extract_audio');

    expect(job.status).toBe('queued');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${BASE}/videos/7/process`);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({ type: 'extract_audio' });
  });

  it('listVideoJobs fetches the video job list', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => [JOB] });

    const jobs = await listVideoJobs(7);

    expect(jobs).toEqual([JOB]);
    expect(fetchMock).toHaveBeenCalledWith(`${BASE}/jobs/video/7`, expect.anything());
  });

  it('cancelJob posts to the cancel endpoint', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ ...JOB, status: 'cancelled' }) });

    const job = await cancelJob(42);

    expect(job.status).toBe('cancelled');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${BASE}/jobs/42/cancel`);
    expect(init.method).toBe('POST');
  });

  it('surfaces conflict errors when a job is already active', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ detail: 'A job of this type is already active' }),
    });

    await expect(processVideo(7, 'extract_audio')).rejects.toThrow('already active');
  });
});
