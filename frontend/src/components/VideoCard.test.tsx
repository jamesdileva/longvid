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

afterEach(() => {
  vi.restoreAllMocks();
});

describe('VideoCard', () => {
  it('renders metadata and media elements', () => {
    render(<VideoCard video={VIDEO} jobs={[]} onExtractAudio={vi.fn()} onDelete={vi.fn()} />);

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
    const onDelete = vi.fn();
    render(<VideoCard video={VIDEO} jobs={[]} onExtractAudio={vi.fn()} onDelete={onDelete} />);

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    expect(onDelete).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Confirm delete' }));
    expect(onDelete).toHaveBeenCalledWith(7);
  });

  it('cancels deletion', () => {
    const onDelete = vi.fn();
    render(<VideoCard video={VIDEO} jobs={[]} onExtractAudio={vi.fn()} onDelete={onDelete} />);

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(onDelete).not.toHaveBeenCalled();
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
    render(<VideoCard video={pending} jobs={[]} onExtractAudio={vi.fn()} onDelete={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByTestId('video-duration')).toHaveTextContent('—');
    });
    expect(screen.queryByAltText(/thumbnail/)).not.toBeInTheDocument();
  });

  it('starts audio extraction when requested', () => {
    const onExtractAudio = vi.fn();
    render(<VideoCard video={VIDEO} jobs={[]} onExtractAudio={onExtractAudio} onDelete={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Extract audio' }));

    expect(onExtractAudio).toHaveBeenCalledWith(VIDEO);
  });

  it('shows a progress bar for an active job', () => {
    render(
      <VideoCard
        video={VIDEO}
        jobs={[makeJob({ status: 'running', progress: 0.45 })]}
        onExtractAudio={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    const progress = screen.getByRole('progressbar') as HTMLProgressElement;
    expect(progress.value).toBeCloseTo(0.45);
    expect(screen.getByTestId('job-percent')).toHaveTextContent('45%');
    expect(screen.getByText('Processing')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Extract audio' })).toBeDisabled();
  });

  it('labels queued jobs', () => {
    render(
      <VideoCard
        video={VIDEO}
        jobs={[makeJob({ status: 'queued', progress: 0 })]}
        onExtractAudio={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expect(screen.getByText('Queued')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('cancels an active job', async () => {
    const cancelSpy = vi.spyOn(jobsService, 'cancelJob').mockResolvedValue(
      makeJob({ status: 'cancelled' }),
    );
    render(
      <VideoCard
        video={VIDEO}
        jobs={[makeJob({ id: 42, status: 'running', progress: 0.2 })]}
        onExtractAudio={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Cancel job' }));

    await waitFor(() => {
      expect(cancelSpy).toHaveBeenCalledWith(42);
    });
  });

  it('shows the error and Retry for a failed job', () => {
    const onExtractAudio = vi.fn();
    render(
      <VideoCard
        video={VIDEO}
        jobs={[makeJob({ status: 'failed', error: 'ffmpeg exited with code 1' })]}
        onExtractAudio={onExtractAudio}
        onDelete={vi.fn()}
      />,
    );

    expect(screen.getByTestId('job-error')).toHaveTextContent('ffmpeg exited with code 1');

    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(onExtractAudio).toHaveBeenCalledWith(VIDEO);
  });

  it('shows the audio-ready badge and disables extraction', () => {
    render(
      <VideoCard
        video={{ ...VIDEO, audio_path: 'media/audio/7.wav' }}
        jobs={[]}
        onExtractAudio={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expect(screen.getByTestId('audio-ready')).toHaveTextContent('extracted');
    expect(screen.getByRole('button', { name: 'Extract audio' })).toBeDisabled();
  });
});
