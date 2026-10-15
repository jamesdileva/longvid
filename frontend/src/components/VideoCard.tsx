import { useEffect, useRef, useState } from 'react';
import { cancelJob } from '../services/jobs';
import { assetUrl } from '../services/videos';
import AnalysisPanel from './AnalysisPanel';
import TranscriptViewer from './TranscriptViewer';
import type { Video } from '../types/video';
import type { Job } from '../types/job';
import { formatDuration, formatFileSize, formatResolution } from '../utils/format';

interface VideoCardProps {
  video: Video;
  jobs: Job[];
  onExtractAudio: (video: Video) => void;
  onTranscribe: (video: Video) => void;
  onAnalyze: (video: Video) => void;
  onGenerateCandidates: (video: Video) => void;
  onDelete: (videoId: number) => void;
  /** Registers the preview <video> element so parents can seek it. */
  registerElement?: (element: HTMLVideoElement | null) => void;
}

const JOB_LABELS: Record<string, string> = {
  extract_audio: 'Extract audio',
  transcribe: 'Transcribe',
  analyze_events: 'Analyze',
  generate_candidates: 'Generate clips',
  score_candidates: 'Re-score clips',
};

export default function VideoCard({
  video,
  jobs,
  onExtractAudio,
  onTranscribe,
  onAnalyze,
  onGenerateCandidates,
  onDelete,
  registerElement,
}: VideoCardProps) {
  const [confirming, setConfirming] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const thumbnail = assetUrl(video.thumbnail_url);
  const preview = assetUrl(video.preview_url);

  useEffect(() => {
    registerElement?.(videoRef.current);
    return () => registerElement?.(null);
  }, [registerElement]);

  const activeJob = jobs.find((job) => job.status === 'queued' || job.status === 'running');
  const latestJob = jobs[0];
  const audioReady = Boolean(video.audio_path);

  async function handleCancel(jobId: number) {
    setCancelling(true);
    try {
      await cancelJob(jobId);
    } finally {
      setCancelling(false);
    }
  }

  function seekTo(seconds: number) {
    const element = videoRef.current;
    if (!element) return;
    element.currentTime = seconds;
    void element.play().catch(() => undefined);
  }

  return (
    <li className="video-card" data-testid="video-card">
      {thumbnail ? (
        <img className="video-thumb" src={thumbnail} alt={`${video.filename} thumbnail`} />
      ) : (
        <div className="video-thumb placeholder" aria-hidden="true" />
      )}
      <div className="video-body">
        <div className="card-header">
          <span className="video-name" title={video.filename}>
            {video.filename}
          </span>
          <span className={`status-pill ${video.status}`}>{video.status}</span>
        </div>
        <dl className="card-stats">
          <dt>Duration</dt>
          <dd data-testid="video-duration">{formatDuration(video.duration_seconds)}</dd>
          <dt>Resolution</dt>
          <dd>{formatResolution(video.width, video.height)}</dd>
          <dt>Size</dt>
          <dd>{formatFileSize(video.file_size_bytes)}</dd>
          <dt>Video</dt>
          <dd>{video.video_codec ?? '—'}</dd>
          <dt>Audio</dt>
          <dd>
            {audioReady ? (
              <span className="status-pill ready" data-testid="audio-ready">
                extracted
              </span>
            ) : (
              <span data-testid="audio-missing">{video.audio_codec ?? 'not extracted'}</span>
            )}
          </dd>
        </dl>
        {preview && (
          <video ref={videoRef} className="video-preview" controls preload="metadata" src={preview} />
        )}

        {activeJob && (
          <div className="job-progress" data-testid="job-progress">
            <div className="job-progress-header">
              <span>
                {activeJob.status === 'queued'
                  ? 'Queued'
                  : `Processing: ${JOB_LABELS[activeJob.type] ?? activeJob.type}`}
              </span>
              <span data-testid="job-percent">{Math.round(activeJob.progress * 100)}%</span>
            </div>
            <progress value={activeJob.progress} max={1} />
            <button
              type="button"
              onClick={() => void handleCancel(activeJob.id)}
              disabled={cancelling}
            >
              Cancel job
            </button>
          </div>
        )}

        {!activeJob && latestJob?.status === 'failed' && (
          <p className="error-note" role="alert" data-testid="job-error">
            {latestJob.error ?? 'Job failed'}
          </p>
        )}

        <div className="card-actions">
          <button
            type="button"
            onClick={() => onExtractAudio(video)}
            disabled={Boolean(activeJob) || audioReady}
          >
            {JOB_LABELS.extract_audio}
          </button>
          <button
            type="button"
            onClick={() => onTranscribe(video)}
            disabled={Boolean(activeJob) || !audioReady}
          >
            {JOB_LABELS.transcribe}
          </button>
          <button
            type="button"
            onClick={() => onAnalyze(video)}
            disabled={Boolean(activeJob) || !audioReady}
          >
            {JOB_LABELS.analyze_events}
          </button>
          <button
            type="button"
            onClick={() => onGenerateCandidates(video)}
            disabled={Boolean(activeJob) || !audioReady}
          >
            {JOB_LABELS.generate_candidates}
          </button>
          <button type="button" onClick={() => setShowAnalysis((value) => !value)}>
            {showAnalysis ? 'Hide analysis' : 'Show analysis'}
          </button>
          {audioReady && (
            <button type="button" onClick={() => setShowTranscript((value) => !value)}>
              {showTranscript ? 'Hide transcript' : 'Show transcript'}
            </button>
          )}
          {!activeJob && latestJob?.status === 'failed' && (
            <button
              type="button"
              onClick={() =>
                latestJob.type === 'transcribe' ? onTranscribe(video) : onExtractAudio(video)
              }
            >
              Retry
            </button>
          )}
          {confirming ? (
            <>
              <button
                type="button"
                className="danger"
                onClick={() => {
                  setConfirming(false);
                  onDelete(video.id);
                }}
              >
                Confirm delete
              </button>
              <button type="button" onClick={() => setConfirming(false)}>
                Cancel
              </button>
            </>
          ) : (
            <button type="button" onClick={() => setConfirming(true)}>
              Delete
            </button>
          )}
        </div>

        {showTranscript && audioReady && (
          <TranscriptViewer videoId={video.id} onSeek={seekTo} />
        )}

        {showAnalysis && <AnalysisPanel videoId={video.id} onSeek={seekTo} />}
      </div>
    </li>
  );
}
