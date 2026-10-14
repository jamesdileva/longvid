import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ProjectDetail from './ProjectDetail';
import * as projectsService from '../services/projects';
import type { Project } from '../types/project';

const PROJECT: Project = {
  id: 'a'.repeat(32),
  name: 'Gaming Session',
  description: 'Ranked grind',
  status: 'active',
  workspace_path: 'projects/' + 'a'.repeat(32),
  video_count: 0,
  clip_count: 0,
  created_at: '2026-10-13T14:00:00',
  updated_at: '2026-10-13T14:00:00',
};

function renderDetail(id = PROJECT.id) {
  return render(
    <MemoryRouter initialEntries={[`/projects/${id}`]}>
      <Routes>
        <Route path="/projects/:id" element={<ProjectDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('ProjectDetail page', () => {
  it('renders project metadata', async () => {
    vi.spyOn(projectsService, 'getProject').mockResolvedValue(PROJECT);

    renderDetail();

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Gaming Session');
    });
    expect(screen.getByTestId('project-status')).toHaveTextContent('active');
    expect(screen.getByText('Ranked grind')).toBeInTheDocument();
    expect(screen.getByText(`projects/${PROJECT.id}`)).toBeInTheDocument();
    expect(screen.getAllByText('Oct 13, 2026, 2:00 PM')).toHaveLength(2);
  });

  it('archives an active project', async () => {
    vi.spyOn(projectsService, 'getProject').mockResolvedValue(PROJECT);
    const updateSpy = vi
      .spyOn(projectsService, 'updateProject')
      .mockResolvedValue({ ...PROJECT, status: 'archived' });

    renderDetail();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Archive' })).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: 'Archive' }));

    await waitFor(() => {
      expect(screen.getByTestId('project-status')).toHaveTextContent('archived');
    });
    expect(updateSpy).toHaveBeenCalledWith(PROJECT.id, { status: 'archived' });
  });

  it('shows an error when the project is missing', async () => {
    vi.spyOn(projectsService, 'getProject').mockRejectedValue(new Error('Project not found'));

    renderDetail('f'.repeat(32));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Project not found');
    });
  });
});
