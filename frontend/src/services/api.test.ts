import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchHealth } from './api';

const HEALTH_FIXTURE = { status: 'ok', version: '0.1.0', database: 'ok' };

describe('fetchHealth', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('parses the health response', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => HEALTH_FIXTURE });

    const health = await fetchHealth();

    expect(health).toEqual(HEALTH_FIXTURE);
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8790/api/health',
      expect.anything(),
    );
  });

  it('throws when the backend responds with an error status', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 503, json: async () => ({}) });

    await expect(fetchHealth()).rejects.toThrow('503');
  });

  it('throws when the backend is unreachable', async () => {
    fetchMock.mockRejectedValue(new Error('network down'));

    await expect(fetchHealth()).rejects.toThrow('network down');
  });
});
