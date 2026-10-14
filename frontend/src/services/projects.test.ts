import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createProject, deleteProject, getProject, listProjects, updateProject } from './projects';

const PROJECT = {
  id: 'a'.repeat(32),
  name: 'Gaming Session',
  description: null,
  status: 'active' as const,
  workspace_path: 'projects/' + 'a'.repeat(32),
  video_count: 0,
  clip_count: 0,
  created_at: '2026-10-13T14:00:00',
  updated_at: '2026-10-13T14:00:00',
};

const BASE = 'http://127.0.0.1:8790/api';

describe('projects service', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('listProjects calls GET /projects', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => [PROJECT] });

    const projects = await listProjects();

    expect(projects).toEqual([PROJECT]);
    expect(fetchMock).toHaveBeenCalledWith(`${BASE}/projects`, expect.anything());
  });

  it('getProject calls GET /projects/{id}', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => PROJECT });

    await getProject(PROJECT.id);

    expect(fetchMock).toHaveBeenCalledWith(`${BASE}/projects/${PROJECT.id}`, expect.anything());
  });

  it('createProject posts the payload', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => PROJECT });

    await createProject({ name: 'Gaming Session', description: null });

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${BASE}/projects`);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({ name: 'Gaming Session', description: null });
  });

  it('updateProject patches with partial payload', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ ...PROJECT, status: 'archived' }) });

    const updated = await updateProject(PROJECT.id, { status: 'archived' });

    expect(updated.status).toBe('archived');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${BASE}/projects/${PROJECT.id}`);
    expect(init.method).toBe('PATCH');
  });

  it('deleteProject sends DELETE and resolves on 204', async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 204, json: async () => ({}) });

    await expect(deleteProject(PROJECT.id)).resolves.toBeUndefined();

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${BASE}/projects/${PROJECT.id}`);
    expect(init.method).toBe('DELETE');
  });

  it('surfaces backend error details', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Project not found' }),
    });

    await expect(getProject('missing')).rejects.toThrow('Project not found');
  });
});
