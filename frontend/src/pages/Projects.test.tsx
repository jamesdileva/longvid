import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Projects from './Projects';
import * as projectsService from '../services/projects';
import type { Project } from '../types/project';

const PROJECTS: Project[] = [
  {
    id: 'a'.repeat(32),
    name: 'Gaming Session',
    description: 'Ranked grind',
    status: 'active',
    workspace_path: 'projects/' + 'a'.repeat(32),
    video_count: 2,
    clip_count: 0,
    created_at: '2026-10-13T14:00:00',
    updated_at: '2026-10-13T15:04:00',
  },
  {
    id: 'b'.repeat(32),
    name: 'Podcast Pilot',
    description: null,
    status: 'archived',
    workspace_path: 'projects/' + 'b'.repeat(32),
    video_count: 0,
    clip_count: 0,
    created_at: '2026-10-12T09:30:00',
    updated_at: '2026-10-12T09:30:00',
  },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <Projects />
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('Projects page', () => {
  it('renders project cards with stats', async () => {
    vi.spyOn(projectsService, 'listProjects').mockResolvedValue(PROJECTS);

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId('project-list')).toBeInTheDocument();
    });
    const cards = screen.getAllByTestId('project-card');
    expect(cards).toHaveLength(2);
    expect(screen.getByText('Gaming Session')).toBeInTheDocument();
    expect(screen.getAllByTestId('video-count')[0]).toHaveTextContent('2 videos');
    expect(screen.getAllByTestId('last-modified')[0]).toHaveTextContent('Oct 13, 2026, 3:04 PM');
    expect(screen.getByText('Podcast Pilot')).toBeInTheDocument();
  });

  it('shows the empty state when there are no projects', async () => {
    vi.spyOn(projectsService, 'listProjects').mockResolvedValue([]);

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId('projects-empty')).toBeInTheDocument();
    });
  });

  it('creates a project and prepends it to the list', async () => {
    vi.spyOn(projectsService, 'listProjects').mockResolvedValue([]);
    const createSpy = vi.spyOn(projectsService, 'createProject').mockResolvedValue({
      ...PROJECTS[0],
      id: 'c'.repeat(32),
      name: 'Fresh Project',
      description: null,
      video_count: 0,
    });

    renderPage();
    await waitFor(() => expect(screen.getByTestId('projects-empty')).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText('Project name'), { target: { value: 'Fresh Project' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create project' }));

    await waitFor(() => {
      expect(screen.getByText('Fresh Project')).toBeInTheDocument();
    });
    expect(createSpy).toHaveBeenCalledWith({ name: 'Fresh Project', description: null });
  });

  it('requires a name before submitting', async () => {
    vi.spyOn(projectsService, 'listProjects').mockResolvedValue([]);

    renderPage();
    await waitFor(() => expect(screen.getByTestId('projects-empty')).toBeInTheDocument());

    expect(screen.getByRole('button', { name: 'Create project' })).toBeDisabled();
  });

  it('deletes a project after inline confirmation', async () => {
    vi.spyOn(projectsService, 'listProjects').mockResolvedValue([PROJECTS[0]]);
    const deleteSpy = vi
      .spyOn(projectsService, 'deleteProject')
      .mockResolvedValue(undefined);

    renderPage();
    await waitFor(() => expect(screen.getByText('Gaming Session')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirm delete' }));

    await waitFor(() => {
      expect(screen.queryByText('Gaming Session')).not.toBeInTheDocument();
    });
    expect(deleteSpy).toHaveBeenCalledWith(PROJECTS[0].id);
  });

  it('shows an error when loading fails', async () => {
    vi.spyOn(projectsService, 'listProjects').mockRejectedValue(new Error('backend down'));

    renderPage();

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('backend down');
    });
  });
});
