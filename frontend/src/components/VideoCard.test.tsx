import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import VideoCard from './VideoCard';
import * as jobsService from '../services/jobs';
import type { Video } from '../types/video';
import type { Job } from '../types/job';

const VIDEO: Video = {
  id: 7,
  project_id: 'a'.repeat(32),
  filename: 'stream_recording.mp4',
  status: 'ready',
  duration_seconds: 95.4,
  width: 1920,
  height: 1080,
  fps: 60,
  video_codec: 'h264',
  audio_codec: 'aac',
  sample_rate: 48000,
  channels: 2,
  file_size_bytes: 2 * 1024 * 1024,
  thumbnail_url: '/api/videos/7/thumbnail',
  preview_url: '/api/videos/7/preview',
  audio_path: null,
  created_at: '2026-10-13T14:00:00',
  updated_at: '2026-10-13T14:00:00',
};

function makeJob(overrides: Partial<Job> = {}): Job {
  return {
    id: 1,
    video_id: VIDEO.id,
    type: 'extract_audio',
    status: 'completed',
    progress: 1,
    error: null,
    started_at: '2026-10-13T14:01:00',
    completed_at: '2026-10-13T14:01:05',
    created_at: '2026-10-13T14:00:30',
    updated_at: '2026-10-13T14:01:05',
    ...overrides,
  };
}

function renderCard(video: Video = VIDEO, jobs: Job[] = []) {
  const handlers = {
    onExtractAudio: vi.fn(),
    onTranscribe: vi.fn(),
    onAnalyze: vi.fn(),
    onTrackSubjects: vi.fn(),
    onGenerateCandidates: vi.fn(),
    onDelete: vi.fn(),
  };
  render(<VideoCard video={video} jobs={jobs} {...handlers} />);
  return handlers;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('VideoCard', () => {
  it('renders metadata and media elements', () => {
    renderCard();

    expect(screen.getByText('stream_recording.mp4')).toBeInTheDocument();
    expect(screen.getByTestId('video-duration')).toHaveTextContent('1:35');
    expect(screen.getByText('1920 × 1080')).toBeInTheDocument();
    expect(screen.getByText('2 MB')).toBeInTheDocument();

    const thumb = screen.getByAltText('stream_recording.mp4 thumbnail') as HTMLImageElement;
    expect(thumb.src).toBe('http://127.0.0.1:8790/api/videos/7/thumbnail');

    const preview = screen.getByTestId('video-card').querySelector('video');
    expect(preview?.getAttribute('src')).toBe('http://127.0.0.1:8790/api/videos/7/preview');
  });

  it('deletes only after inline confirmation', () => {
    const handlers = renderCard();

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    expect(handlers.onDelete).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Confirm delete' }));
    expect(handlers.onDelete).toHaveBeenCalledWith(7);
  });

  it('cancels deletion', () => {
    const handlers = renderCard();

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(handlers.onDelete).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
  });

  it('handles videos without preview assets', async () => {
    const pending: Video = {
      ...VIDEO,
      status: 'pending',
      thumbnail_url: null,
      preview_url: null,
      duration_seconds: null,
      width: null,
      height: null,
      file_size_bytes: null,
    };
    renderCard(pending);

    await waitFor(() => {
      expect(screen.getByTestId('video-duration')).toHaveTextContent('—');
    });
    expect(screen.queryByAltText(/thumbnail/)).not.toBeInTheDocument();
  });

  it('starts audio extraction when requested', () => {
    const handlers = renderCard(); // no audio_path yet

    fireEvent.click(screen.getByRole('button', { name: 'Extract audio' }));

    expect(handlers.onExtractAudio).toHaveBeenCalledWith(VIDEO);
  });

  it('shows a progress bar for an active job', () => {
    renderCard(VIDEO, [makeJob({ status: 'running', progress: 0.45 })]);

    const progress = screen.getByRole('progressbar') as HTMLProgressElement;
    expect(progress.value).toBeCloseTo(0.45);
    expect(screen.getByTestId('job-percent')).toHaveTextContent('45%');
    expect(screen.getByText('Processing: Extract audio')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Extract audio' })).toBeDisabled();
  });

  it('labels queued jobs', () => {
    renderCard(VIDEO, [makeJob({ status: 'queued', progress: 0 })]);

    expect(screen.getByText('Queued')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('labels a running transcription job', () => {
    renderCard({ ...VIDEO, audio_path: 'media/audio/7.wav' }, [
      makeJob({ type: 'transcribe', status: 'running', progress: 0.6 }),
    ]);

    expect(screen.getByText('Processing: Transcribe')).toBeInTheDocument();
  });

  it('labels a running analysis job', () => {
    renderCard({ ...VIDEO, audio_path: 'media/audio/7.wav' }, [
      makeJob({ type: 'analyze_events', status: 'running', progress: 0.3 }),
    ]);

    expect(screen.getByText('Processing: Analyze')).toBeInTheDocument();
  });

  it('starts subject tracking when requested', () => {
    const handlers = renderCard();

    fireEvent.click(screen.getByRole('button', { name: 'Track subjects' }));

    expect(handlers.onTrackSubjects).toHaveBeenCalledWith(VIDEO);
  });

  it('labels a running subject-tracking job', () => {
    renderCard(VIDEO, [makeJob({ type: 'track_subjects', status: 'running', progress: 0.5 })]);

    expect(screen.getByText('Processing: Track subjects')).toBeInTheDocument();
  });

  it('cancels an active job', async () => {
    const cancelSpy = vi.spyOn(jobsService, 'cancelJob').mockResolvedValue(makeJob({ status: 'cancelled' }));
    renderCard(VIDEO, [makeJob({ id: 42, status: 'running', progress: 0.2 })]);

    fireEvent.click(screen.getByRole('button', { name: 'Cancel job' }));

    await waitFor(() => {
      expect(cancelSpy).toHaveBeenCalledWith(42);
    });
  });

  it('shows the error and Retry for a failed job', () => {
    const handlers = renderCard(VIDEO, [
      makeJob({ status: 'failed', error: 'ffmpeg exited with code 1' }),
    ]);

    expect(screen.getByTestId('job-error')).toHaveTextContent('ffmpeg exited with code 1');

    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(handlers.onExtractAudio).toHaveBeenCalledWith(VIDEO);
  });

  it('retries a failed transcription job by re-transcribing', () => {
    const handlers = renderCard({ ...VIDEO, audio_path: 'media/audio/7.wav' }, [
      makeJob({ type: 'transcribe', status: 'failed', error: 'model unavailable' }),
    ]);

    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));

    expect(handlers.onTranscribe).toHaveBeenCalled();
  });

  it('shows the audio-ready badge and disables extraction', () => {
    renderCard({ ...VIDEO, audio_path: 'media/audio/7.wav' });

    expect(screen.getByTestId('audio-ready')).toHaveTextContent('extracted');
    expect(screen.getByRole('button', { name: 'Extract audio' })).toBeDisabled();
  });

  it('enables transcription only once audio is extracted', () => {
    const handlers = renderCard();

    expect(screen.getByRole('button', { name: 'Transcribe' })).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: 'Extract audio' }));
    expect(handlers.onExtractAudio).toHaveBeenCalled();
  });

  it('starts transcription when audio is ready', () => {
    const handlers = renderCard({ ...VIDEO, audio_path: 'media/audio/7.wav' });

    fireEvent.click(screen.getByRole('button', { name: 'Transcribe' }));

    expect(handlers.onTranscribe).toHaveBeenCalledWith({ ...VIDEO, audio_path: 'media/audio/7.wav' });
  });

  it('starts analysis when audio is ready', () => {
    const handlers = renderCard({ ...VIDEO, audio_path: 'media/audio/7.wav' });

    fireEvent.click(screen.getByRole('button', { name: 'Analyze' }));

    expect(handlers.onAnalyze).toHaveBeenCalledWith({ ...VIDEO, audio_path: 'media/audio/7.wav' });
  });

  it('starts candidate detection when audio is ready', () => {
    const handlers = renderCard({ ...VIDEO, audio_path: 'media/audio/7.wav' });

    fireEvent.click(screen.getByRole('button', { name: 'Detect highlights' }));

    expect(handlers.onGenerateCandidates).toHaveBeenCalled();
  });

  it('disables detection until audio is extracted', () => {
    renderCard();

    expect(screen.getByRole('button', { name: 'Detect highlights' })).toBeDisabled();
  });

  it('labels a running candidate detection job', () => {
    renderCard({ ...VIDEO, audio_path: 'media/audio/7.wav' }, [
      makeJob({ type: 'generate_candidates', status: 'running', progress: 0.8 }),
    ]);

    expect(screen.getByText('Processing: Detect highlights')).toBeInTheDocument();
  });

  it('labels a running clip generation job', () => {
    renderCard({ ...VIDEO, audio_path: 'media/audio/7.wav' }, [
      makeJob({ type: 'generate_clip', status: 'running', progress: 0.4 }),
    ]);

    expect(screen.getByText('Processing: Generate clips')).toBeInTheDocument();
  });

  it('disables analysis until audio is extracted', () => {
    renderCard();

    expect(screen.getByRole('button', { name: 'Analyze' })).toBeDisabled();
  });

  it('toggles the analysis panel', async () => {
    const analysis = await import('../services/analysis');
    vi.spyOn(analysis, 'listScenes').mockResolvedValue([]);
    vi.spyOn(analysis, 'listEvents').mockResolvedValue([]);
    renderCard({ ...VIDEO, audio_path: 'media/audio/7.wav' });

    fireEvent.click(screen.getByRole('button', { name: 'Show analysis' }));

    await waitFor(() => {
      expect(screen.getByTestId('analysis-panel')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Hide analysis' }));
    expect(screen.queryByTestId('analysis-panel')).not.toBeInTheDocument();
  });

  it('toggles the transcript viewer when audio exists', async () => {
    renderCard({ ...VIDEO, audio_path: 'media/audio/7.wav' });

    fireEvent.click(screen.getByRole('button', { name: 'Show transcript' }));

    await waitFor(() => {
      expect(screen.getByText(/Loading transcript|Run transcription/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Hide transcript' }));
    expect(screen.queryByText(/Loading transcript/)).not.toBeInTheDocument();
  });
});
