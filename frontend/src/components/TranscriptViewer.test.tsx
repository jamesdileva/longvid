import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import TranscriptViewer from './TranscriptViewer';
import * as transcriptsService from '../services/transcripts';

const TRANSCRIPT = {
  id: 1,
  video_id: 7,
  language: null,
  duration_seconds: 12.0,
  created_at: '2026-10-13T14:05:00',
  segments: [
    {
      id: 1,
      position: 0,
      start_seconds: 0,
      end_seconds: 5,
      text: 'So here is where everything went wrong.',
      confidence: 0.94,
    },
    {
      id: 2,
      position: 1,
      start_seconds: 5,
      end_seconds: 10,
      text: 'Wait... hold on. No way.',
      confidence: 0.91,
    },
    {
      id: 3,
      position: 2,
      start_seconds: 10,
      end_seconds: 12,
      text: 'I thought this was impossible.',
      confidence: null,
    },
  ],
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe('TranscriptViewer', () => {
  it('renders segments with timestamps', async () => {
    vi.spyOn(transcriptsService, 'getTranscript').mockResolvedValue(TRANSCRIPT);

    render(<TranscriptViewer videoId={7} onSeek={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByTestId('transcript')).toBeInTheDocument();
    });
    expect(screen.getByText('0:00')).toBeInTheDocument();
    expect(screen.getByText('0:05')).toBeInTheDocument();
    expect(screen.getByText('0:10')).toBeInTheDocument();
    expect(screen.getByText('So here is where everything went wrong.')).toBeInTheDocument();
  });

  it('seeks the video when a segment is clicked', async () => {
    vi.spyOn(transcriptsService, 'getTranscript').mockResolvedValue(TRANSCRIPT);
    const onSeek = vi.fn();

    render(<TranscriptViewer videoId={7} onSeek={onSeek} />);
    await waitFor(() => expect(screen.getByTestId('transcript')).toBeInTheDocument());

    fireEvent.click(screen.getByText('Wait... hold on. No way.'));

    expect(onSeek).toHaveBeenCalledWith(5);
  });

  it('explains when no transcript exists yet', async () => {
    vi.spyOn(transcriptsService, 'getTranscript').mockRejectedValue(
      new Error('Request to /videos/7/transcript failed: No transcript yet'),
    );

    render(<TranscriptViewer videoId={7} onSeek={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(/Run transcription to generate one/)).toBeInTheDocument();
    });
  });

  it('shows other errors verbatim', async () => {
    vi.spyOn(transcriptsService, 'getTranscript').mockRejectedValue(new Error('backend down'));

    render(<TranscriptViewer videoId={7} onSeek={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('backend down')).toBeInTheDocument();
    });
  });
});
