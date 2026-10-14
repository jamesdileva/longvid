import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ProjectDetail from './ProjectDetail';
import * as projectsService from '../services/projects';
import * as videosService from '../services/videos';
import type { Project } from '../types/project';
import type { Video } from '../types/video';

const PROJECT: Project = {
  id: 'a'.repeat(32),
  name: 'Gaming Session',
  description: 'Ranked grind',
  status: 'active',
  workspace_path: 'projects/' + 'a'.repeat(32),
  video_count: 1,
  clip_count: 0,
  created_at: '2026-10-13T14:00:00',
  updated_at: '2026-10-13T16:45:00',
};

const VIDEO: Video = {
  id: 7,
  project_id: PROJECT.id,
  filename: 'stream_recording.mp4',
  status: 'ready',
  duration_seconds: 3600,
  width: 1920,
  height: 1080,
  fps: 60,
  video_codec: 'h264',
  audio_codec: 'aac',
  sample_rate: 48000,
  channels: 2,
  file_size_bytes: 1024 * 1024 * 512,
  thumbnail_url: '/api/videos/7/thumbnail',
  preview_url: '/api/videos/7/preview',
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

describe('ProjectDetail videos section', () => {
  it('lists imported videos', async () => {
    vi.spyOn(projectsService, 'getProject').mockResolvedValue(PROJECT);
    vi.spyOn(videosService, 'listVideos').mockResolvedValue([VIDEO]);

    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId('video-list')).toBeInTheDocument();
    });
    expect(screen.getByText('stream_recording.mp4')).toBeInTheDocument();
    expect(screen.getAllByTestId('video-duration')[0]).toHaveTextContent('1:00:00');
    expect(screen.queryByTestId('videos-empty')).not.toBeInTheDocument();
  });

  it('imports a video and refreshes the list', async () => {
    vi.spyOn(projectsService, 'getProject').mockResolvedValue(PROJECT);
    const listSpy = vi
      .spyOn(videosService, 'listVideos')
      .mockResolvedValueOnce([])
      .mockResolvedValue([VIDEO]);
    const importSpy = vi.spyOn(videosService, 'importVideo').mockResolvedValue(VIDEO);

    renderDetail();
    await waitFor(() => expect(screen.getByTestId('videos-empty')).toBeInTheDocument());

    const { fireEvent } = await import('@testing-library/react');
    fireEvent.change(screen.getByLabelText('Video file path'), {
      target: { value: 'D:/clips/stream.mp4' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Import video' }));

    await waitFor(() => {
      expect(screen.getByText('stream_recording.mp4')).toBeInTheDocument();
    });
    expect(importSpy).toHaveBeenCalledWith(PROJECT.id, 'D:/clips/stream.mp4');
    expect(listSpy).toHaveBeenCalledTimes(2);
  });

  it('shows import errors', async () => {
    vi.spyOn(projectsService, 'getProject').mockResolvedValue(PROJECT);
    vi.spyOn(videosService, 'listVideos').mockResolvedValue([]);
    vi.spyOn(videosService, 'importVideo').mockRejectedValue(new Error('Unsupported file type. Allowed: .mp4'));

    renderDetail();
    const { fireEvent } = await import('@testing-library/react');
    await waitFor(() => expect(screen.getByTestId('videos-empty')).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText('Video file path'), { target: { value: 'x.txt' } });
    fireEvent.click(screen.getByRole('button', { name: 'Import video' }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Unsupported file type');
    });
  });

  it('shows an error when the project is missing', async () => {
    vi.spyOn(projectsService, 'getProject').mockRejectedValue(new Error('Project not found'));
    vi.spyOn(videosService, 'listVideos').mockResolvedValue([]);

    renderDetail('f'.repeat(32));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Project not found');
    });
  });

  it('renders project metadata and archives on demand', async () => {
    vi.spyOn(projectsService, 'getProject').mockResolvedValue(PROJECT);
    vi.spyOn(videosService, 'listVideos').mockResolvedValue([]);
    const updateSpy = vi
      .spyOn(projectsService, 'updateProject')
      .mockResolvedValue({ ...PROJECT, status: 'archived' });

    renderDetail();
    const { fireEvent } = await import('@testing-library/react');

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Gaming Session');
    });
    expect(screen.getByText('Ranked grind')).toBeInTheDocument();
    expect(screen.getByText(`projects/${PROJECT.id}`)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Archive' }));

    await waitFor(() => {
      expect(screen.getByTestId('project-status')).toHaveTextContent('archived');
    });
    expect(updateSpy).toHaveBeenCalledWith(PROJECT.id, { status: 'archived' });
  });
});
