import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ClipsPanel from './ClipsPanel';
import * as clipsService from '../services/clips';
import type { Clip } from '../types/clip';

const VIDEOS = [
  { id: 7, filename: 'stream_recording.mp4' },
  { id: 9, filename: 'podcast.mp4' },
];

function clip(overrides: Partial<Clip> = {}): Clip {
  return {
    id: 1,
    video_id: 7,
    candidate_id: 3,
    title: 'Best play',
    start_seconds: 812.2,
    end_seconds: 851.8,
    duration_seconds: 39.6,
    editing_profile: 'clean',
    status: 'ready',
    file_size_bytes: 5_242_880,
    error: null,
    file_url: '/api/clips/1/file',
    created_at: '2026-10-14T10:05:00',
    updated_at: '2026-10-14T10:05:00',
    ...overrides,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('ClipsPanel', () => {
  it('renders ready clips with a player', async () => {
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([clip()]);

    render(<ClipsPanel projectId="p" videos={VIDEOS} />);

    await waitFor(() => expect(screen.getByTestId('clip-card')).toBeInTheDocument());
    expect(screen.getByText('Best play')).toBeInTheDocument();
    expect(screen.getByTestId('clip-player')).toHaveAttribute(
      'src',
      expect.stringContaining('/api/clips/1/file'),
    );
    expect(screen.getByTestId('clip-status')).toHaveTextContent('ready');
    expect(within(screen.getByTestId('clip-card')).getByText('stream_recording.mp4')).toBeInTheDocument();
  });

  it('shows the empty state before generation', async () => {
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([]);

    render(<ClipsPanel projectId="p" videos={VIDEOS} />);

    await waitFor(() => expect(screen.getByTestId('clips-empty')).toBeInTheDocument());
  });

  it('generates top clips for the selected video and notifies the parent', async () => {
    const listSpy = vi
      .spyOn(clipsService, 'listProjectClips')
      .mockResolvedValueOnce([])
      .mockResolvedValue([clip()]);
    const generateSpy = vi
      .spyOn(clipsService, 'generateClips')
      .mockResolvedValue({ job_id: 20, status: 'queued', clip_count: 1 });
    const onJobsChanged = vi.fn();

    render(<ClipsPanel projectId="p" videos={VIDEOS} onJobsChanged={onJobsChanged} />);
    await waitFor(() => expect(screen.getByTestId('clips-empty')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: 'Generate Top 5' }));

    await waitFor(() => {
      expect(generateSpy).toHaveBeenCalledWith(7, { selection: 'top5' });
    });
    expect(onJobsChanged).toHaveBeenCalledWith(7);
    expect(listSpy).toHaveBeenCalledTimes(2);
  });

  it('uses the chosen video for batch generation', async () => {
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([]);
    const generateSpy = vi
      .spyOn(clipsService, 'generateClips')
      .mockResolvedValue({ job_id: 21, status: 'queued', clip_count: 3 });

    render(<ClipsPanel projectId="p" videos={VIDEOS} />);
    await waitFor(() => expect(screen.getByTestId('clips-empty')).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText('Clip source video'), { target: { value: '9' } });
    fireEvent.click(screen.getByRole('button', { name: 'Generate All' }));

    await waitFor(() => {
      expect(generateSpy).toHaveBeenCalledWith(9, { selection: 'all' });
    });
  });

  it('surfaces generation errors', async () => {
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([]);
    vi.spyOn(clipsService, 'generateClips').mockRejectedValue(
      new Error('Request to /videos/7/generate-clips failed: No candidates; detect highlights first'),
    );

    render(<ClipsPanel projectId="p" videos={VIDEOS} />);
    await waitFor(() => expect(screen.getByTestId('clips-empty')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: 'Generate Top 10' }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('detect highlights first');
    });
  });

  it('deletes a clip', async () => {
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([clip()]);
    const deleteSpy = vi.spyOn(clipsService, 'deleteClip').mockResolvedValue(undefined);

    render(<ClipsPanel projectId="p" videos={VIDEOS} />);
    await waitFor(() => expect(screen.getByTestId('clip-card')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));

    await waitFor(() => expect(deleteSpy).toHaveBeenCalledWith(1));
    expect(screen.queryByTestId('clip-card')).not.toBeInTheDocument();
  });

  it('shows failed clip errors', async () => {
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([
      clip({ status: 'failed', file_url: null, error: 'Clip cut failed' }),
    ]);

    render(<ClipsPanel projectId="p" videos={VIDEOS} />);

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Clip cut failed'));
    expect(screen.queryByTestId('clip-player')).not.toBeInTheDocument();
  });
});
