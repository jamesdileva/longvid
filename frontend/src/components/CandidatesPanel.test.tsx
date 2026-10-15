import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import CandidatesPanel from './CandidatesPanel';
import * as candidatesService from '../services/candidates';
import type { Candidate, CandidateStatus } from '../types/candidate';

const VIDEOS = [
  { id: 7, filename: 'stream_recording.mp4' },
  { id: 9, filename: 'podcast.mp4' },
];

function candidate(overrides: Partial<Candidate> = {}): Candidate {
  return {
    id: 1,
    video_id: 7,
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
    created_at: '2026-10-14T10:00:00',
    updated_at: '2026-10-14T10:00:00',
    ...overrides,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('CandidatesPanel', () => {
  it('renders candidates sorted by overall score', async () => {
    vi.spyOn(candidatesService, 'listProjectCandidates').mockResolvedValue([
      candidate({ id: 1, overall_score: 0.86, category: 'reaction' }),
      candidate({
        id: 2,
        overall_score: 0.4,
        category: 'filler',
        reason: 'meh',
        start_seconds: 120,
        end_seconds: 180,
      }),
    ]);

    render(
      <CandidatesPanel projectId="p" videos={VIDEOS} onSeekVideo={vi.fn()} />,
    );

    await waitFor(() => {
      expect(screen.getByTestId('candidate-list')).toBeInTheDocument();
    });
    const scores = screen.getAllByTestId('candidate-score');
    expect(scores).toHaveLength(2);
    expect(scores[0]).toHaveTextContent('86');
    expect(scores[1]).toHaveTextContent('40');
    expect(screen.getByText('reaction')).toBeInTheDocument();
    expect(screen.getByText('High-energy reaction followed by a win')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /13:32/ })).toBeInTheDocument();
    expect(screen.getAllByText('stream_recording.mp4')).toHaveLength(2);
  });

  it('accepts and rejects candidates', async () => {
    vi.spyOn(candidatesService, 'listProjectCandidates').mockResolvedValue([candidate()]);
    const updateSpy = vi
      .spyOn(candidatesService, 'updateCandidateStatus')
      .mockImplementation(
        async (id: number, status: CandidateStatus) => candidate({ id, status }),
      );

    render(<CandidatesPanel projectId="p" videos={VIDEOS} onSeekVideo={vi.fn()} />);
    await waitFor(() => expect(screen.getByTestId('candidate-card')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: 'Accept' }));
    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(1, 'accepted');
    });
    expect(screen.getByRole('button', { name: 'Accept' })).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: 'Reject' }));
    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(1, 'rejected');
    });
  });

  it('seeks the owning video when the timestamp is clicked', async () => {
    vi.spyOn(candidatesService, 'listProjectCandidates').mockResolvedValue([
      candidate({ video_id: 9 }),
    ]);
    const onSeekVideo = vi.fn();

    render(<CandidatesPanel projectId="p" videos={VIDEOS} onSeekVideo={onSeekVideo} />);
    await waitFor(() => expect(screen.getByTestId('candidate-card')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /13:32/ }));

    expect(onSeekVideo).toHaveBeenCalledWith(9, 812.2);
  });

  it('shows the empty state before generation', async () => {
    vi.spyOn(candidatesService, 'listProjectCandidates').mockResolvedValue([]);

    render(<CandidatesPanel projectId="p" videos={VIDEOS} onSeekVideo={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByTestId('candidates-empty')).toBeInTheDocument();
    });
  });

  it('shows load errors', async () => {
    vi.spyOn(candidatesService, 'listProjectCandidates').mockRejectedValue(
      new Error('backend down'),
    );

    render(<CandidatesPanel projectId="p" videos={VIDEOS} onSeekVideo={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('backend down');
    });
  });
});
