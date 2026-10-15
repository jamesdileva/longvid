import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import AnalysisPanel from './AnalysisPanel';
import * as analysisService from '../services/analysis';

const SCENES = [
  { id: 1, video_id: 7, position: 0, start_seconds: 0, end_seconds: 6.2, score: 0.42 },
  { id: 2, video_id: 7, position: 1, start_seconds: 6.2, end_seconds: 12.4, score: null },
];

const EVENTS = [
  {
    id: 1,
    video_id: 7,
    type: 'scene_change',
    start_seconds: 6.2,
    end_seconds: 6.2,
    confidence: 0.42,
    source: 'scene_detection',
    payload: { score: 0.42 },
    created_at: '2026-10-13T15:00:00',
  },
  {
    id: 2,
    video_id: 7,
    type: 'silence',
    start_seconds: 7,
    end_seconds: 12,
    confidence: 0.99,
    source: 'audio_analysis',
    payload: { mean_rms_db: -61 },
    created_at: '2026-10-13T15:00:00',
  },
];

afterEach(() => {
  vi.restoreAllMocks();
});

describe('AnalysisPanel', () => {
  it('renders scene and event summaries', async () => {
    vi.spyOn(analysisService, 'listScenes').mockResolvedValue(SCENES);
    vi.spyOn(analysisService, 'listEvents').mockResolvedValue(EVENTS);

    render(<AnalysisPanel videoId={7} onSeek={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByTestId('analysis-panel')).toBeInTheDocument();
    });
    expect(screen.getByTestId('scene-count')).toHaveTextContent('2 scenes');
    expect(screen.getByTestId('event-count')).toHaveTextContent('2 events');
    expect(screen.getByText('scene change: 1')).toBeInTheDocument();
    expect(screen.getByText('silence: 1')).toBeInTheDocument();
    expect(screen.getAllByTestId('event-list')[0]).toBeInTheDocument();
  });

  it('seeks when an event row is clicked', async () => {
    vi.spyOn(analysisService, 'listScenes').mockResolvedValue(SCENES);
    vi.spyOn(analysisService, 'listEvents').mockResolvedValue(EVENTS);
    const onSeek = vi.fn();

    render(<AnalysisPanel videoId={7} onSeek={onSeek} />);
    await waitFor(() => expect(screen.getByTestId('event-list')).toBeInTheDocument());

    fireEvent.click(screen.getByText('silence'));

    expect(onSeek).toHaveBeenCalledWith(7);
  });

  it('shows the empty state before analysis runs', async () => {
    vi.spyOn(analysisService, 'listScenes').mockResolvedValue([]);
    vi.spyOn(analysisService, 'listEvents').mockResolvedValue([]);

    render(<AnalysisPanel videoId={7} onSeek={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(/Run Analyze to detect/)).toBeInTheDocument();
    });
    expect(screen.getByTestId('scene-count')).toHaveTextContent('0 scenes');
  });

  it('shows load errors', async () => {
    vi.spyOn(analysisService, 'listScenes').mockRejectedValue(new Error('backend down'));
    vi.spyOn(analysisService, 'listEvents').mockResolvedValue([]);

    render(<AnalysisPanel videoId={7} onSeek={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('backend down')).toBeInTheDocument();
    });
  });
});
