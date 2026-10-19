import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ClipsPanel from './ClipsPanel';
import * as clipsService from '../services/clips';
import * as editingProfilesService from '../services/editingProfiles';
import * as exportsService from '../services/exports';
import type { Clip } from '../types/clip';
import type { EditingProfile } from '../types/editingProfile';
import type { Export, ExportPreset } from '../types/export';

const VIDEOS = [
  { id: 7, filename: 'stream_recording.mp4' },
  { id: 9, filename: 'podcast.mp4' },
];

const PROFILES: EditingProfile[] = [
  {
    key: 'clean',
    label: 'Clean',
    description: 'Raw cut',
    aspect_ratio: 'original',
    captions: false,
    zoom: false,
    audio_normalization: false,
    max_duration_seconds: null,
    pacing: 'relaxed',
  },
  {
    key: 'shorts',
    label: 'Shorts',
    description: 'Vertical captioned',
    aspect_ratio: '9:16',
    captions: true,
    zoom: true,
    audio_normalization: true,
    max_duration_seconds: 60,
    pacing: 'standard',
  },
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
    editing_plan: {
      plan_version: 1,
      profile: 'clean',
      source: 'source/stream_recording.mp4',
      start: 812.2,
      end: 851.8,
      aspect_ratio: 'original',
      captions: false,
      zoom: false,
      audio_normalization: false,
    },
    status: 'ready',
    file_size_bytes: 5_242_880,
    error: null,
    file_url: '/api/clips/1/file',
    caption_srt_url: null,
    caption_ass_url: null,
    created_at: '2026-10-14T10:05:00',
    updated_at: '2026-10-14T10:05:00',
    ...overrides,
  };
}

const PRESETS: ExportPreset[] = [
  {
    key: 'youtube',
    label: 'YouTube',
    description: 'H.264 1080p',
    container: 'mp4',
    video_codec: 'h264',
    audio_codec: 'aac',
    crf: 20,
    encoder_preset: 'medium',
    max_width: 1920,
    audio_bitrate: '192k',
  },
  {
    key: 'archive',
    label: 'Local archive',
    description: 'H.265 full-resolution',
    container: 'mp4',
    video_codec: 'h265',
    audio_codec: 'aac',
    crf: 20,
    encoder_preset: 'slow',
    max_width: null,
    audio_bitrate: '320k',
  },
];

function exportRow(overrides: Partial<Export> = {}): Export {
  return {
    id: 5,
    clip_id: 1,
    project_id: 'p'.repeat(32),
    preset: 'youtube',
    container: 'mp4',
    video_codec: 'h264',
    audio_codec: 'aac',
    settings: { crf: 20 },
    editing_profile: 'clean',
    plan_snapshot: null,
    app_version: '0.1.0',
    status: 'ready',
    file_size_bytes: 1024,
    error: null,
    file_url: '/api/exports/5/file',
    created_at: '2026-10-14T10:05:00',
    updated_at: '2026-10-14T10:05:00',
    ...overrides,
  };
}

beforeEach(() => {
  vi.spyOn(editingProfilesService, 'listEditingProfiles').mockResolvedValue(PROFILES);
  vi.spyOn(exportsService, 'listExportPresets').mockResolvedValue(PRESETS);
  vi.spyOn(exportsService, 'listProjectExports').mockResolvedValue([]);
});

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
      expect(generateSpy).toHaveBeenCalledWith(7, { selection: 'top5', editingProfile: 'clean' });
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
      expect(generateSpy).toHaveBeenCalledWith(9, { selection: 'all', editingProfile: 'clean' });
    });
  });

  it('generates with the selected editing profile', async () => {
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([]);
    const generateSpy = vi
      .spyOn(clipsService, 'generateClips')
      .mockResolvedValue({ job_id: 22, status: 'queued', clip_count: 1 });

    render(<ClipsPanel projectId="p" videos={VIDEOS} />);
    await waitFor(() => expect(screen.getByTestId('clips-empty')).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText('Editing profile'), { target: { value: 'shorts' } });
    fireEvent.click(screen.getByRole('button', { name: 'Generate Top 5' }));

    await waitFor(() => {
      expect(generateSpy).toHaveBeenCalledWith(7, {
        selection: 'top5',
        editingProfile: 'shorts',
      });
    });
  });

  it('shows the editing profile and plan on a clip', async () => {
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([
      clip({
        editing_profile: 'shorts',
        editing_plan: {
          plan_version: 1,
          profile: 'shorts',
          source: 'source/stream_recording.mp4',
          start: 0,
          end: 30,
          aspect_ratio: '9:16',
          captions: true,
          zoom: true,
          audio_normalization: true,
        },
      }),
    ]);

    render(<ClipsPanel projectId="p" videos={VIDEOS} />);

    await waitFor(() => expect(screen.getByTestId('clip-card')).toBeInTheDocument());
    expect(screen.getByTestId('clip-profile')).toHaveTextContent('Shorts');
    const plan = screen.getByTestId('clip-plan');
    expect(plan).toHaveTextContent('9:16');
    expect(plan).toHaveTextContent('captions');
    expect(plan).toHaveTextContent('zoom');
    expect(screen.queryByTestId('clip-trim')).not.toBeInTheDocument();
  });

  it('shows the reframed output resolution for converted clips', async () => {
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([
      clip({
        editing_profile: 'shorts',
        editing_plan: {
          plan_version: 1,
          profile: 'shorts',
          source: 'source/stream_recording.mp4',
          start: 0,
          end: 30,
          aspect_ratio: '9:16',
          captions: true,
          zoom: true,
          audio_normalization: true,
          framing: {
            target_width: 1080,
            target_height: 1920,
            crop_width: 528,
            crop_height: 938,
            crop_x: 696,
            crop_y: 70,
            zoom: 1.15,
            filter: 'crop=528:938:696:70,scale=1080:1920,setsar=1',
          },
        },
      }),
    ]);

    render(<ClipsPanel projectId="p" videos={VIDEOS} />);

    await waitFor(() => expect(screen.getByTestId('clip-framing')).toBeInTheDocument());
    expect(screen.getByTestId('clip-framing')).toHaveTextContent('1080x1920');
  });

  it('marks a subject-tracked dynamic crop', async () => {
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([
      clip({
        editing_profile: 'shorts',
        editing_plan: {
          plan_version: 1,
          profile: 'shorts',
          source: 'source/stream_recording.mp4',
          start: 0,
          end: 30,
          aspect_ratio: '9:16',
          captions: true,
          zoom: true,
          audio_normalization: true,
          framing: {
            target_width: 1080,
            target_height: 1920,
            crop_width: 528,
            crop_height: 938,
            crop_x: 696,
            crop_y: 70,
            zoom: 1.15,
            filter: "crop=528:938:'if(lt(t,0.000),696.000,700.000)':'70.000',scale=1080:1920,setsar=1",
            dynamic: true,
            keyframes: [
              [0, 696, 70],
              [4, 700, 70],
            ],
          },
        },
      }),
    ]);

    render(<ClipsPanel projectId="p" videos={VIDEOS} />);

    await waitFor(() => expect(screen.getByTestId('clip-framing')).toBeInTheDocument());
    expect(screen.getByTestId('clip-framing')).toHaveTextContent('tracked');
  });

  it('offers SRT and ASS caption downloads when present', async () => {
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([
      clip({
        caption_srt_url: '/api/clips/1/captions/srt',
        caption_ass_url: '/api/clips/1/captions/ass',
      }),
    ]);

    render(<ClipsPanel projectId="p" videos={VIDEOS} />);

    await waitFor(() => expect(screen.getByTestId('clip-captions')).toBeInTheDocument());
    const links = within(screen.getByTestId('clip-captions')).getAllByRole('link');
    expect(links.map((link) => link.textContent)).toEqual(['SRT', 'ASS']);
    expect(links[0]).toHaveAttribute('href', expect.stringContaining('/api/clips/1/captions/srt'));
  });

  it('flags clips whose audio was normalized', async () => {
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([
      clip({
        editing_plan: {
          plan_version: 1,
          profile: 'youtube',
          source: 'source/stream_recording.mp4',
          start: 812.2,
          end: 851.8,
          aspect_ratio: '16:9',
          captions: false,
          zoom: false,
          audio_normalization: true,
          audio: {
            loudness_target_lufs: -16,
            true_peak_db: -1.5,
            loudness_range: 11,
            gate_threshold_db: -45,
            filter: 'agate=threshold=-45dB:ratio=2,loudnorm=I=-16:TP=-1.5:LRA=11',
          },
        },
      }),
    ]);

    render(<ClipsPanel projectId="p" videos={VIDEOS} />);

    await waitFor(() => expect(screen.getByTestId('clip-audio')).toBeInTheDocument());
    expect(screen.getByTestId('clip-audio')).toHaveTextContent('audio-norm');
  });

  it('flags clips whose dead air was trimmed', async () => {
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([
      clip({
        editing_plan: {
          plan_version: 1,
          profile: 'clean',
          source: 'source/stream_recording.mp4',
          start: 812.2,
          end: 847.3,
          aspect_ratio: '16:9',
          captions: false,
          zoom: false,
          audio_normalization: false,
          trim: {
            applied: true,
            original_start: 812.2,
            original_end: 851.8,
            sentence_start: false,
            sentence_end: true,
            silence_removed_seconds: 4.5,
          },
        },
      }),
    ]);

    render(<ClipsPanel projectId="p" videos={VIDEOS} />);

    await waitFor(() => expect(screen.getByTestId('clip-trim')).toBeInTheDocument());
    expect(screen.getByTestId('clip-trim')).toHaveTextContent('trimmed 5s');
  });

  it('flags clips whose pacing cut dead air', async () => {
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([
      clip({
        editing_profile: 'tiktok',
        editing_plan: {
          plan_version: 1,
          profile: 'tiktok',
          source: 'source/stream_recording.mp4',
          start: 0,
          end: 40,
          aspect_ratio: '9:16',
          captions: true,
          zoom: true,
          audio_normalization: true,
          pacing: {
            style: 'punchy',
            speech_ratio: 0.6,
            silence_ratio: 0.4,
            scene_changes_per_minute: 8,
            dead_air_runs: [[4.15, 7.85]],
            silence_removed_seconds: 3.7,
            applied: true,
            video_filter: "select='not(between(t,4.150,7.850))',setpts=N/FRAME_RATE/TB",
            audio_filter: "aselect='not(between(t,4.150,7.850))',asetpts=N/SR/TB",
          },
        },
      }),
    ]);

    render(<ClipsPanel projectId="p" videos={VIDEOS} />);

    await waitFor(() => expect(screen.getByTestId('clip-pacing')).toBeInTheDocument());
    expect(screen.getByTestId('clip-pacing')).toHaveTextContent('paced 4s');
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

  it('queues an export for a ready clip with the chosen preset', async () => {
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([clip()]);
    const listExports = vi
      .spyOn(exportsService, 'listProjectExports')
      .mockResolvedValueOnce([])
      .mockResolvedValue([exportRow({ status: 'pending', file_url: null })]);
    const createSpy = vi
      .spyOn(exportsService, 'createExport')
      .mockResolvedValue({ job_id: 30, export_id: 5, status: 'pending' });
    const onJobsChanged = vi.fn();

    render(<ClipsPanel projectId="p" videos={VIDEOS} onJobsChanged={onJobsChanged} />);
    await waitFor(() => expect(screen.getByTestId('clip-card')).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText('Export preset'), { target: { value: 'archive' } });
    fireEvent.click(screen.getByRole('button', { name: 'Export' }));

    await waitFor(() => expect(createSpy).toHaveBeenCalledWith(1, 'archive'));
    expect(onJobsChanged).toHaveBeenCalledWith(7);
    await waitFor(() => expect(screen.getByTestId('export-row')).toBeInTheDocument());
    expect(listExports).toHaveBeenCalled();
  });

  it('offers a download link for a finished export', async () => {
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([clip()]);
    vi.spyOn(exportsService, 'listProjectExports').mockResolvedValue([exportRow()]);

    render(<ClipsPanel projectId="p" videos={VIDEOS} />);

    await waitFor(() => expect(screen.getByTestId('export-row')).toBeInTheDocument());
    expect(screen.getByTestId('export-status')).toHaveTextContent('ready');
    const link = within(screen.getByTestId('export-row')).getByRole('link');
    expect(link).toHaveAttribute('href', expect.stringContaining('/api/exports/5/file'));
    expect(link).toHaveTextContent('Download');
  });

  it('does not offer exports for unrendered clips', async () => {
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([
      clip({ status: 'pending', file_url: null }),
    ]);

    render(<ClipsPanel projectId="p" videos={VIDEOS} />);

    await waitFor(() => expect(screen.getByTestId('clip-card')).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: 'Export' })).not.toBeInTheDocument();
  });

  it('surfaces export errors', async () => {
    vi.spyOn(clipsService, 'listProjectClips').mockResolvedValue([clip()]);
    vi.spyOn(exportsService, 'createExport').mockRejectedValue(
      new Error('Request to /clips/1/export failed: Clip has not been rendered yet'),
    );

    render(<ClipsPanel projectId="p" videos={VIDEOS} />);
    await waitFor(() => expect(screen.getByTestId('clip-card')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: 'Export' }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('has not been rendered yet');
    });
  });
});
