import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import VideoCard from './VideoCard';
import type { Video } from '../types/video';

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
  created_at: '2026-10-13T14:00:00',
  updated_at: '2026-10-13T14:00:00',
};

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('VideoCard', () => {
  it('renders metadata and media elements', () => {
    render(<VideoCard video={VIDEO} onDelete={vi.fn()} />);

    expect(screen.getByText('stream_recording.mp4')).toBeInTheDocument();
    expect(screen.getByTestId('video-duration')).toHaveTextContent('1:35');
    expect(screen.getByText('1920 × 1080')).toBeInTheDocument();
    expect(screen.getByText('2 MB')).toBeInTheDocument();

    const thumb = screen.getByAltText('stream_recording.mp4 thumbnail') as HTMLImageElement;
    expect(thumb.src).toBe('http://127.0.0.1:8790/api/videos/7/thumbnail');

    const preview = screen.getByTestId('video-card').querySelector('video');
    expect(preview?.getAttribute('src')).toBe('http://127.0.0.1:8790/api/videos/7/preview');
  });

  it('deletes only after inline confirmation', async () => {
    const onDelete = vi.fn();
    render(<VideoCard video={VIDEO} onDelete={onDelete} />);

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    expect(onDelete).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Confirm delete' }));
    expect(onDelete).toHaveBeenCalledWith(7);
  });

  it('cancels deletion', () => {
    const onDelete = vi.fn();
    render(<VideoCard video={VIDEO} onDelete={onDelete} />);

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(onDelete).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
  });

  it('handles videos without preview assets', async () => {
    const pending: Video = { ...VIDEO, status: 'pending', thumbnail_url: null, preview_url: null, duration_seconds: null, width: null, height: null, file_size_bytes: null };
    render(<VideoCard video={pending} onDelete={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByTestId('video-duration')).toHaveTextContent('—');
    });
    expect(screen.queryByAltText(/thumbnail/)).not.toBeInTheDocument();
  });
});
