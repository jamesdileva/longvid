import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ProjectDetail from './ProjectDetail';
import * as projectsService from '../services/projects';
import * as videosService from '../services/videos';
import * as jobsService from '../services/jobs';
import * as candidatesService from '../services/candidates';
import * as clipsService from '../services/clips';
import * as editingProfilesService from '../services/editingProfiles';
import * as exportsService from '../services/exports';
import type { Project } from '../types/project';
import type { Video } from '../types/video';
import type { Job } from '../types/job';
import type { Candidate } from '../types/candidate';
import type { Clip } from '../types/clip';

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
  audio_path: null,
  created_at: '2026-10-13T14:00:00',
  updated_at: '2026-10-13T14:00:00',
};

const CANDIDATE: Candidate = {
  id: 3,
  video_id: VIDEO.id,
  start_seconds: 812.2,
  end_seconds: 851.8,
  status: 'pending',
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
  thumbnail_url: '/api/candidates/3/thumbnail',
  created_at: '2026-10-14T10:00:00',
  updated_at: '2026-10-14T10:00:00',
};

const CLIP: Clip = {
  id: 21,
  video_id: VIDEO.id,
  candidate_id: 3,
  title: 'High-energy reaction followed by a win',
  start_seconds: 812.2,
  end_seconds: 851.8,
  duration_seconds: 39.6,
  editing_profile: 'clean',
  editing_plan: {
    plan_version: 1,
    profile: 'clean',
    source: 'source/stream_recording.mp4',
    start: 812.2,
    end: 851.8,
    aspect_ratio: '16:9',
    captions: false,
    zoom: false,
    audio_normalization: false,
  },
  status: 'ready',
  file_size_bytes: 5_242_880,
  error: null,
  file_url: '/api/clips/21/file',
  caption_srt_url: null,
  caption_ass_url: null,
  created_at: '2026-10-14T10:05:00',
  updated_at: '2026-10-14T10:05:00',
};

const COMPLETED_JOB: Job = {
  id: 3,
  video_id: VIDEO.id,
  type: 'extract_audio',
  status: 'completed',
  progress: 1,
  error: null,
  started_at: '2026-10-13T14:01:00',
  completed_at: '2026-10-13T14:01:05',
  created_at: '2026-10-13T14:00:30',
  updated_at: '2026-10-13T14:01:05',
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

/** Base mocks: project loads, one video, no jobs, no candidates. */
function mockBase() {
  vi.spyOn(projectsService, 'getProject').mockResolvedValue(PROJECT);
  vi.spyOn(videosService, 'listVideos').mockResolvedValue([VIDEO]);
  vi.spyOn(jobsService, 'listVideoJobs').mockResolvedValue([]);
  vi.spyOn(candidatesService, 'listProjectCandidates').mockResolvedValue([]);
}

beforeEach(() => {
  vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([]);
  vi.spyOn(editingProfilesService, 'listEditingProfiles').mockResolvedValue([]);
  vi.spyOn(exportsService, 'listExportPresets').mockResolvedValue([]);
  vi.spyOn(exportsService, 'listProjectExports').mockResolvedValue([]);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe('ProjectDetail videos section', () => {
  it('lists imported videos', async () => {
    mockBase();

    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId('video-list')).toBeInTheDocument();
    });
    expect(
      within(screen.getByTestId('video-list')).getByText('stream_recording.mp4'),
    ).toBeInTheDocument();
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
    vi.spyOn(jobsService, 'listVideoJobs').mockResolvedValue([]);

    renderDetail();
    await waitFor(() => expect(screen.getByTestId('videos-empty')).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText('Video file path'), {
      target: { value: 'D:/clips/stream.mp4' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Import video' }));

    await waitFor(() => {
      expect(
        within(screen.getByTestId('video-list')).getByText('stream_recording.mp4'),
      ).toBeInTheDocument();
    });
    expect(importSpy).toHaveBeenCalledWith(PROJECT.id, 'D:/clips/stream.mp4');
    expect(listSpy).toHaveBeenCalledTimes(2);
  });

  it('shows import errors', async () => {
    vi.spyOn(projectsService, 'getProject').mockResolvedValue(PROJECT);
    vi.spyOn(videosService, 'listVideos').mockResolvedValue([]);
    vi.spyOn(jobsService, 'listVideoJobs').mockResolvedValue([]);
    vi.spyOn(candidatesService, 'listProjectCandidates').mockResolvedValue([]);
    vi.spyOn(videosService, 'importVideo').mockRejectedValue(new Error('Unsupported file type. Allowed: .mp4'));

    renderDetail();
    await waitFor(() => expect(screen.getByTestId('videos-empty')).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText('Video file path'), { target: { value: 'x.txt' } });
    fireEvent.click(screen.getByRole('button', { name: 'Import video' }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Unsupported file type');
    });
  });

  it('starts an extraction job and polls until it settles', async () => {
    vi.spyOn(projectsService, 'getProject').mockResolvedValue(PROJECT);
    const videosSpy = vi
      .spyOn(videosService, 'listVideos')
      .mockResolvedValueOnce([VIDEO])
      // after the job settles the server reports the extracted audio
      .mockResolvedValue([{ ...VIDEO, audio_path: 'media/audio/7.wav' }]);
    const jobsSpy = vi
      .spyOn(jobsService, 'listVideoJobs')
      .mockResolvedValueOnce([])
      // queued -> running -> completed across polls
      .mockResolvedValueOnce([{ ...COMPLETED_JOB, status: 'queued', progress: 0 }])
      .mockResolvedValueOnce([{ ...COMPLETED_JOB, status: 'running', progress: 0.5 }])
      .mockResolvedValue([COMPLETED_JOB]);
    vi.spyOn(jobsService, 'processVideo').mockResolvedValue({
      ...COMPLETED_JOB,
      status: 'queued',
      progress: 0,
    });

    vi.useFakeTimers({ shouldAdvanceTime: true });
    renderDetail();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Extract audio' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Extract audio' }));

    await waitFor(() => {
      expect(screen.getByTestId('job-progress')).toBeInTheDocument();
    });
    expect(screen.getByTestId('job-percent')).toHaveTextContent('0%');

    // advance past the polling interval until polling stops on its own
    await vi.advanceTimersByTimeAsync(10000);

    expect(jobsSpy.mock.calls.length).toBeGreaterThan(2);
    expect(screen.queryByTestId('job-progress')).not.toBeInTheDocument();
    expect(screen.getByTestId('audio-ready')).toBeInTheDocument();
    expect(videosSpy.mock.calls.length).toBeGreaterThan(1);
  });

  it('shows failed job errors with a retry', async () => {
    vi.spyOn(projectsService, 'getProject').mockResolvedValue(PROJECT);
    vi.spyOn(videosService, 'listVideos').mockResolvedValue([VIDEO]);
    vi.spyOn(jobsService, 'listVideoJobs').mockResolvedValue([
      { ...COMPLETED_JOB, status: 'failed', error: 'ffmpeg exited with code 1' },
    ]);
    const processSpy = vi
      .spyOn(jobsService, 'processVideo')
      .mockResolvedValue({ ...COMPLETED_JOB, status: 'queued', progress: 0 });

    renderDetail();
    await waitFor(() => {
      expect(screen.getByTestId('job-error')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));

    await waitFor(() => {
      expect(processSpy).toHaveBeenCalledWith(VIDEO.id, 'extract_audio');
    });
  });

  it('shows an error when the project is missing', async () => {
    vi.spyOn(projectsService, 'getProject').mockRejectedValue(new Error('Project not found'));
    vi.spyOn(videosService, 'listVideos').mockResolvedValue([]);
    vi.spyOn(jobsService, 'listVideoJobs').mockResolvedValue([]);

    renderDetail('f'.repeat(32));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Project not found');
    });
  });

  it('shows generated candidates with accept/reject', async () => {
    mockBase();
    vi.spyOn(candidatesService, 'listProjectCandidates').mockResolvedValue([CANDIDATE]);
    const updateSpy = vi
      .spyOn(candidatesService, 'updateCandidateStatus')
      .mockImplementation(
        async (id: number, status: 'accepted' | 'rejected' | 'pending') => ({
          ...CANDIDATE,
          id,
          status,
        }),
      );

    renderDetail();
    await waitFor(() => {
      expect(screen.getByTestId('candidates-panel')).toBeInTheDocument();
    });
    expect(screen.getByTestId('candidate-score')).toHaveTextContent('86');

    fireEvent.click(screen.getByRole('button', { name: 'Accept' }));
    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(3, 'accepted');
    });
  });

  it('starts a generation job from the video card', async () => {
    mockBase();
    vi.spyOn(videosService, 'listVideos').mockResolvedValue([
      { ...VIDEO, audio_path: 'media/audio/7.wav' },
    ]);
    const generateSpy = vi
      .spyOn(candidatesService, 'generateCandidates')
      .mockResolvedValue({ job_id: 12, status: 'queued' });

    renderDetail();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Detect highlights' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Detect highlights' }));

    await waitFor(() => {
      expect(generateSpy).toHaveBeenCalledWith(VIDEO.id);
    });
  });

  it('renders clips and generates top clips for the selected video', async () => {
    mockBase();
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([CLIP]);
    const generateSpy = vi
      .spyOn(clipsService, 'generateClips')
      .mockResolvedValue({ job_id: 20, status: 'queued', clip_count: 1 });

    renderDetail();
    await waitFor(() => expect(screen.getByTestId('clip-card')).toBeInTheDocument());
    expect(screen.getByText('High-energy reaction followed by a win')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Generate Top 5' }));

    await waitFor(() => {
      expect(generateSpy).toHaveBeenCalledWith(VIDEO.id, {
        selection: 'top5',
        editingProfile: 'clean',
      });
    });
  });

  it('renders project metadata and archives on demand', async () => {
    mockBase();
    const updateSpy = vi
      .spyOn(projectsService, 'updateProject')
      .mockResolvedValue({ ...PROJECT, status: 'archived' });

    renderDetail();

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
