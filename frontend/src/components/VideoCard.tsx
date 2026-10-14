import { useState } from 'react';
import { assetUrl } from '../services/videos';
import type { Video } from '../types/video';
import { formatDuration, formatFileSize, formatResolution } from '../utils/format';

interface VideoCardProps {
  video: Video;
  onDelete: (videoId: number) => void;
}

export default function VideoCard({ video, onDelete }: VideoCardProps) {
  const [confirming, setConfirming] = useState(false);
  const thumbnail = assetUrl(video.thumbnail_url);
  const preview = assetUrl(video.preview_url);

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
          <dd>{video.audio_codec ?? 'none'}</dd>
        </dl>
        {preview && (
          <video className="video-preview" controls preload="metadata" src={preview} />
        )}
        <div className="card-actions">
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
