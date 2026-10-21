import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { listContentProfiles, updateContentProfile } from './contentProfiles';

const PROFILES = [
  {
    key: 'general',
    label: 'General',
    description: 'Broad semantic scoring',
    guidance: 'Score broadly.',
    keywords: [],
    category: 'highlight',
  },
  {
    key: 'gaming',
    label: 'Gaming',
    description: 'Kills and clutches',
    guidance: 'Prioritize kills.',
    keywords: ['kill', 'clutch'],
    category: 'gaming',
  },
];

const BASE = 'http://127.0.0.1:8790/api';

describe('contentProfiles service', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('listContentProfiles fetches the catalog', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => PROFILES });

    const profiles = await listContentProfiles();

    expect(profiles).toEqual(PROFILES);
    expect(fetchMock).toHaveBeenCalledWith(`${BASE}/content-profiles`, expect.anything());
  });

  it('updateContentProfile puts the selection', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ id: 7, content_profile: 'gaming' }) });

    const video = await updateContentProfile(7, 'gaming');

    expect(video).toEqual({ id: 7, content_profile: 'gaming' });
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/videos/7/content-profile`,
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ content_profile: 'gaming' }),
      }),
    );
  });
});
