import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { listEditingProfiles } from './editingProfiles';

const PROFILES = [
  {
    key: 'clean',
    label: 'Clean',
    description: 'Raw landscape cut',
    aspect_ratio: 'original',
    captions: false,
    zoom: false,
    audio_normalization: false,
    max_duration_seconds: null,
    pacing: 'relaxed',
    hook: false,
  },
  {
    key: 'shorts',
    label: 'Shorts',
    description: 'Vertical captioned clip',
    aspect_ratio: '9:16',
    captions: true,
    zoom: true,
    audio_normalization: true,
    max_duration_seconds: 60,
    pacing: 'standard',
    hook: true,
  },
];

const BASE = 'http://127.0.0.1:8790/api';

describe('editingProfiles service', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('listEditingProfiles fetches the catalog', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => PROFILES });

    const profiles = await listEditingProfiles();

    expect(profiles).toEqual(PROFILES);
    expect(fetchMock).toHaveBeenCalledWith(`${BASE}/editing-profiles`, expect.anything());
  });
});
