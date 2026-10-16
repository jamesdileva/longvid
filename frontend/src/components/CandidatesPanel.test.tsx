import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import CandidatesPanel from './CandidatesPanel';
import * as candidatesService from '../services/candidates';
import type { Candidate, CandidateStatus } from '../types/candidate';

const VIDEOS = [
  { id: 7, filename: 'stream_recording.mp4', preview_url: '/api/videos/7/preview' },
  { id: 9, filename: 'podcast.mp4', preview_url: '/api/videos/9/preview' },
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
    thumbnail_url: '/api/candidates/1/thumbnail',
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

  it('renders a thumbnail per candidate', async () => {
    vi.spyOn(candidatesService, 'listProjectCandidates').mockResolvedValue([candidate()]);

    render(<CandidatesPanel projectId="p" videos={VIDEOS} onSeekVideo={vi.fn()} />);
    await waitFor(() => expect(screen.getByTestId('candidate-thumb')).toBeInTheDocument());

    expect(screen.getByTestId('candidate-thumb')).toHaveAttribute(
      'src',
      expect.stringContaining('/api/candidates/1/thumbnail'),
    );
  });

  it('filters candidates by category', async () => {
    vi.spyOn(candidatesService, 'listProjectCandidates').mockResolvedValue([
      candidate({ id: 1, category: 'funny', reason: 'a joke lands' }),
      candidate({ id: 2, category: 'reaction', reason: 'huge reaction' }),
    ]);

    render(<CandidatesPanel projectId="p" videos={VIDEOS} onSeekVideo={vi.fn()} />);
    await waitFor(() => expect(screen.getAllByTestId('candidate-card')).toHaveLength(2));

    fireEvent.click(screen.getByRole('button', { name: 'Funny' }));

    const cards = screen.getAllByTestId('candidate-card');
    expect(cards).toHaveLength(1);
    expect(cards[0]).toHaveTextContent('a joke lands');
  });

  it('keeps only the top five with the Best filter', async () => {
    const scores = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4];
    vi.spyOn(candidatesService, 'listProjectCandidates').mockResolvedValue(
      scores.map((overall_score, index) =>
        candidate({ id: index + 1, overall_score, reason: `score ${overall_score}` }),
      ),
    );

    render(<CandidatesPanel projectId="p" videos={VIDEOS} onSeekVideo={vi.fn()} />);
    await waitFor(() => expect(screen.getAllByTestId('candidate-card')).toHaveLength(6));

    fireEvent.click(screen.getByRole('button', { name: 'Best' }));

    expect(screen.getAllByTestId('candidate-card')).toHaveLength(5);
    expect(screen.queryByText('score 0.4')).not.toBeInTheDocument();
  });

  it('sorts candidates by duration', async () => {
    vi.spyOn(candidatesService, 'listProjectCandidates').mockResolvedValue([
      candidate({
        id: 1,
        reason: 'short',
        start_seconds: 0,
        end_seconds: 10,
        overall_score: 0.9,
      }),
      candidate({
        id: 2,
        reason: 'long',
        start_seconds: 100,
        end_seconds: 140,
        overall_score: 0.5,
      }),
    ]);

    render(<CandidatesPanel projectId="p" videos={VIDEOS} onSeekVideo={vi.fn()} />);
    await waitFor(() => expect(screen.getAllByTestId('candidate-card')).toHaveLength(2));

    fireEvent.change(screen.getByLabelText('Sort candidates'), { target: { value: 'duration' } });

    const cards = screen.getAllByTestId('candidate-card');
    expect(cards[0]).toHaveTextContent('long');
  });

  it('opens an in-range preview player', async () => {
    vi.spyOn(candidatesService, 'listProjectCandidates').mockResolvedValue([candidate()]);

    const { container } = render(
      <CandidatesPanel projectId="p" videos={VIDEOS} onSeekVideo={vi.fn()} />,
    );
    await waitFor(() => expect(screen.getByTestId('candidate-card')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: 'Preview' }));

    expect(screen.getByTestId('candidate-preview')).toBeInTheDocument();
    expect(screen.getByTestId('preview-seek')).toHaveAttribute('min', '812.2');
    expect(container.querySelector('video')).toHaveAttribute(
      'src',
      expect.stringContaining('/api/videos/7/preview'),
    );
  });
});
