import { useCallback, useEffect, useMemo, useState } from 'react';
import { deleteClip, generateClips, listProjectClips } from '../services/clips';
import { listEditingProfiles } from '../services/editingProfiles';
import { createExport, listExportPresets, listProjectExports } from '../services/exports';
import { assetUrl } from '../services/videos';
import type { Clip, ClipSelection } from '../types/clip';
import type { EditingProfile } from '../types/editingProfile';
import type { Export, ExportPreset } from '../types/export';
import { formatDuration, formatFileSize } from '../utils/format';

interface ClipVideo {
  id: number;
  filename: string;
}

interface ClipsPanelProps {
  projectId: string;
  videos: ClipVideo[];
  /** Notify the parent that a new render job was queued (to refresh jobs). */
  onJobsChanged?: (videoId: number) => void;
}

const POLL_INTERVAL_MS = 1500;

const BATCH_ACTIONS: { selection: ClipSelection; label: string }[] = [
  { selection: 'top5', label: 'Generate Top 5' },
  { selection: 'top10', label: 'Generate Top 10' },
  { selection: 'all', label: 'Generate All' },
];

export default function ClipsPanel({ projectId, videos, onJobsChanged }: ClipsPanelProps) {
  const [clips, setClips] = useState<Clip[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedVideoId, setSelectedVideoId] = useState<number | null>(null);
  const [profiles, setProfiles] = useState<EditingProfile[]>([]);
  const [profileKey, setProfileKey] = useState('clean');
  const [generating, setGenerating] = useState(false);
  const [presets, setPresets] = useState<ExportPreset[]>([]);
  const [presetKey, setPresetKey] = useState('youtube');
  const [exports, setExports] = useState<Export[]>([]);
  const [exportingClipId, setExportingClipId] = useState<number | null>(null);

  const filenameById = useMemo(
    () => new Map(videos.map((video) => [video.id, video.filename])),
    [videos],
  );
  const labelByKey = useMemo(
    () => new Map(profiles.map((profile) => [profile.key, profile.label])),
    [profiles],
  );

  useEffect(() => {
    let active = true;
    listEditingProfiles()
      .then((loaded) => {
        if (active) setProfiles(loaded);
      })
      .catch(() => {
        if (active) setProfiles([]);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    listExportPresets()
      .then((loaded) => {
        if (!active) return;
        setPresets(loaded);
        if (loaded.length > 0) setPresetKey(loaded[0].key);
      })
      .catch(() => {
        if (active) setPresets([]);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (selectedVideoId === null && videos.length > 0) {
      setSelectedVideoId(videos[0].id);
    }
  }, [videos, selectedVideoId]);

  const load = useCallback(async () => {
    try {
      const [loaded, loadedExports] = await Promise.all([
        listProjectClips(projectId),
        listProjectExports(projectId),
      ]);
      setClips(loaded);
      setExports(loadedExports);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load clips');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    setLoading(true);
    void load();
  }, [load]);

  const hasUnfinished = clips.some(
    (clip) => clip.status === 'pending' || clip.status === 'generating',
  );
  const hasUnfinishedExports = exports.some(
    (item) => item.status === 'pending' || item.status === 'processing',
  );
  useEffect(() => {
    if (!hasUnfinished && !hasUnfinishedExports) return;
    const timer = setInterval(() => {
      void load();
    }, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [hasUnfinished, hasUnfinishedExports, load]);

  const exportsByClip = useMemo(() => {
    const map = new Map<number, Export[]>();
    for (const item of exports) {
      const list = map.get(item.clip_id) ?? [];
      list.push(item);
      map.set(item.clip_id, list);
    }
    return map;
  }, [exports]);

  async function handleGenerate(selection: ClipSelection) {
    if (selectedVideoId === null) return;
    setGenerating(true);
    setError(null);
    try {
      await generateClips(selectedVideoId, { selection, editingProfile: profileKey });
      onJobsChanged?.(selectedVideoId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start clip generation');
    } finally {
      setGenerating(false);
    }
  }

  async function handleDelete(clipId: number) {
    setError(null);
    try {
      await deleteClip(clipId);
      setClips((current) => current.filter((clip) => clip.id !== clipId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete clip');
    }
  }

  async function handleExport(clip: Clip) {
    setExportingClipId(clip.id);
    setError(null);
    try {
      await createExport(clip.id, presetKey);
      onJobsChanged?.(clip.video_id);
      setExports(await listProjectExports(projectId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start export');
    } finally {
      setExportingClipId(null);
    }
  }

  if (loading) return <p className="empty-note">Loading clips…</p>;

  return (
    <div className="clips-panel" data-testid="clips-panel">
      {error && (
        <p className="error-note" role="alert">
          {error}
        </p>
      )}

      {videos.length > 0 && (
        <div className="clip-toolbar">
          <label className="clip-video-select">
            Video
            <select
              value={selectedVideoId ?? ''}
              aria-label="Clip source video"
              onChange={(event) => setSelectedVideoId(Number(event.target.value))}
            >
              {videos.map((video) => (
                <option key={video.id} value={video.id}>
                  {video.filename}
                </option>
              ))}
            </select>
          </label>
          {profiles.length > 0 && (
            <label className="clip-profile-select">
              Profile
              <select
                value={profileKey}
                aria-label="Editing profile"
                onChange={(event) => setProfileKey(event.target.value)}
              >
                {profiles.map((profile) => (
                  <option key={profile.key} value={profile.key}>
                    {profile.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          {presets.length > 0 && (
            <label className="clip-export-select">
              Export
              <select
                value={presetKey}
                aria-label="Export preset"
                onChange={(event) => setPresetKey(event.target.value)}
              >
                {presets.map((preset) => (
                  <option key={preset.key} value={preset.key}>
                    {preset.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          <div className="clip-actions">
            {BATCH_ACTIONS.map((action) => (
              <button
                key={action.selection}
                type="button"
                onClick={() => void handleGenerate(action.selection)}
                disabled={generating}
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {clips.length === 0 ? (
        <p className="empty-note" data-testid="clips-empty">
          No clips yet. Generate top clips from a video to create MP4 files.
        </p>
      ) : (
        <ul className="clip-list" data-testid="clip-list">
          {clips.map((clip) => (
            <li className="clip-card" key={clip.id} data-testid="clip-card">
              <div className="card-header">
                <span className="clip-title">{clip.title ?? `Clip #${clip.id}`}</span>
                <span className={`status-pill ${clip.status}`} data-testid="clip-status">
                  {clip.status}
                </span>
              </div>
              <p className="clip-meta">
                <span>{formatDuration(clip.duration_seconds)}</span>
                <span data-testid="clip-profile">
                  {labelByKey.get(clip.editing_profile) ?? clip.editing_profile}
                </span>
                {clip.editing_plan && (
                  <span className="clip-plan" data-testid="clip-plan">
                    <span>{clip.editing_plan.aspect_ratio}</span>
                    {clip.editing_plan.framing && (
                      <span data-testid="clip-framing">
                        {clip.editing_plan.framing.target_width}x
                        {clip.editing_plan.framing.target_height}
                        {clip.editing_plan.framing.dynamic ? ' tracked' : ''}
                      </span>
                    )}
                    {clip.editing_plan.captions && <span>captions</span>}
                    {clip.editing_plan.zoom && <span>zoom</span>}
                    {clip.editing_plan.audio && (
                      <span data-testid="clip-audio">audio-norm</span>
                    )}
                    {clip.editing_plan.trim?.applied &&
                      clip.editing_plan.trim.silence_removed_seconds >= 1 && (
                        <span data-testid="clip-trim">
                          trimmed {Math.round(clip.editing_plan.trim.silence_removed_seconds)}s
                        </span>
                      )}
                    {clip.editing_plan.pacing?.applied && (
                      <span data-testid="clip-pacing">
                        paced {Math.round(clip.editing_plan.pacing.silence_removed_seconds)}s
                      </span>
                    )}
                  </span>
                )}
                {clip.file_size_bytes !== null && <span>{formatFileSize(clip.file_size_bytes)}</span>}
                <span className="clip-video">
                  {filenameById.get(clip.video_id) ?? `video #${clip.video_id}`}
                </span>
              </p>
              {clip.status === 'ready' && clip.file_url && (
                <video
                  className="clip-player"
                  data-testid="clip-player"
                  controls
                  preload="metadata"
                  src={assetUrl(clip.file_url) ?? undefined}
                />
              )}
              {clip.status === 'failed' && clip.error && (
                <p className="error-note" role="alert">
                  {clip.error}
                </p>
              )}
              {clip.caption_srt_url && (
                <p className="clip-captions" data-testid="clip-captions">
                  Captions:
                  <a href={assetUrl(clip.caption_srt_url) ?? undefined} download>
                    SRT
                  </a>
                  {clip.caption_ass_url && (
                    <a href={assetUrl(clip.caption_ass_url) ?? undefined} download>
                      ASS
                    </a>
                  )}
                </p>
              )}
              {(exportsByClip.get(clip.id)?.length ?? 0) > 0 && (
                <ul className="export-list" data-testid="export-list">
                  {(exportsByClip.get(clip.id) ?? []).map((item) => (
                    <li key={item.id} className="export-row" data-testid="export-row">
                      <span className="export-preset">{item.preset}</span>
                      <span className={`status-pill ${item.status}`} data-testid="export-status">
                        {item.status}
                      </span>
                      {item.status === 'ready' && item.file_url && (
                        <a href={assetUrl(item.file_url) ?? undefined} download>
                          Download
                        </a>
                      )}
                      {item.status === 'failed' && item.error && (
                        <span className="error-note">{item.error}</span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              <div className="card-actions">
                {clip.status === 'ready' && presets.length > 0 && (
                  <button
                    type="button"
                    onClick={() => void handleExport(clip)}
                    disabled={exportingClipId === clip.id}
                  >
                    Export
                  </button>
                )}
                <button type="button" onClick={() => void handleDelete(clip.id)}>
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
