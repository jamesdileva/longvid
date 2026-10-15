import { useState } from 'react';
import { cancelJob } from '../services/jobs';
import type { Video } from '../types/video';
import type { Job } from '../types/job';
import { assetUrl } from '../services/videos';
import { formatDuration, formatFileSize, formatResolution } from '../utils/format';

interface VideoCardProps {
  video: Video;
  jobs: Job[];
  onExtractAudio: (video: Video) => void;
  onDelete: (videoId: number) => void;
}

const JOB_LABELS: Record<string, string> = {
  extract_audio: 'Extract audio',
};

export default function VideoCard({ video, jobs, onExtractAudio, onDelete }: VideoCardProps) {
  const [confirming, setConfirming] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const thumbnail = assetUrl(video.thumbnail_url);
  const preview = assetUrl(video.preview_url);

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
        {preview && <video className="video-preview" controls preload="metadata" src={preview} />}

        {activeJob && (
          <div className="job-progress" data-testid="job-progress">
            <div className="job-progress-header">
              <span>{activeJob.status === 'queued' ? 'Queued' : 'Processing'}</span>
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
          {!activeJob && latestJob?.status === 'failed' && (
            <button type="button" onClick={() => onExtractAudio(video)}>
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
      </div>
    </li>
  );
}
