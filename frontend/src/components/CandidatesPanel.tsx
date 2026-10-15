import { useEffect, useMemo, useState } from 'react';
import { listProjectCandidates, updateCandidateStatus } from '../services/candidates';
import type { Candidate, CandidateStatus } from '../types/candidate';
import { formatDuration } from '../utils/format';

interface CandidatesPanelProps {
  projectId: string;
  videos: { id: number; filename: string }[];
  onSeekVideo: (videoId: number, seconds: number) => void;
}

function statusClass(status: CandidateStatus): string {
  return status;
}

export default function CandidatesPanel({ projectId, videos, onSeekVideo }: CandidatesPanelProps) {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const filenameById = useMemo(
    () => new Map(videos.map((video) => [video.id, video.filename])),
    [videos],
  );

  useEffect(() => {
    let active = true;
    setLoading(true);
    listProjectCandidates(projectId)
      .then((loaded) => {
        if (!active) return;
        setCandidates(loaded);
        setError(null);
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : 'Failed to load candidates');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [projectId]);

  async function setStatus(candidate: Candidate, status: CandidateStatus) {
    try {
      const updated = await updateCandidateStatus(candidate.id, status);
      setCandidates((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update candidate');
    }
  }

  if (loading) return <p className="empty-note">Loading candidates…</p>;
  if (error) {
    return (
      <p className="error-note" role="alert">
        {error}
      </p>
    );
  }

  return (
    <div className="candidates-panel" data-testid="candidates-panel">
      {candidates.length === 0 ? (
        <p className="empty-note" data-testid="candidates-empty">
          No candidates yet. Use “Generate clips” on a video to detect highlights.
        </p>
      ) : (
        <ul className="candidate-list" data-testid="candidate-list">
          {candidates.map((candidate) => (
            <li className="candidate-card" key={candidate.id} data-testid="candidate-card">
              <div className="card-header">
                <span className="candidate-score" data-testid="candidate-score">
                  {Math.round(candidate.overall_score * 100)}
                </span>
                <span className="candidate-meta">
                  <span className="candidate-category">{candidate.category ?? 'detected'}</span>
                  <span className="candidate-source">{candidate.source}</span>
                  <span className={`status-pill ${statusClass(candidate.status)}`}>
                    {candidate.status}
                  </span>
                </span>
              </div>
              <p className="candidate-reason">{candidate.reason}</p>
              <p className="candidate-times">
                <button
                  type="button"
                  className="link-button"
                  onClick={() => onSeekVideo(candidate.video_id, candidate.start_seconds)}
                >
                  {formatDuration(candidate.start_seconds)} – {formatDuration(candidate.end_seconds)}
                </button>
                <span className="candidate-duration">
                  ({formatDuration(candidate.end_seconds - candidate.start_seconds)})
                </span>
                <span className="candidate-video">
                  {filenameById.get(candidate.video_id) ?? `video #${candidate.video_id}`}
                </span>
              </p>
              <dl className="card-stats candidate-scores">
                <dt>Semantic</dt>
                <dd>{Math.round(candidate.semantic_score * 100)}</dd>
                <dt>Audio</dt>
                <dd>{Math.round(candidate.audio_score * 100)}</dd>
                <dt>Visual</dt>
                <dd>{Math.round(candidate.visual_score * 100)}</dd>
                <dt>Context</dt>
                <dd>{Math.round(candidate.context_score * 100)}</dd>
                <dt>Standalone</dt>
                <dd>{Math.round(candidate.standalone_score * 100)}</dd>
                <dt>Novelty</dt>
                <dd>{Math.round(candidate.novelty_score * 100)}</dd>
              </dl>
              <div className="card-actions">
                <button
                  type="button"
                  onClick={() => void setStatus(candidate, 'accepted')}
                  disabled={candidate.status === 'accepted'}
                >
                  Accept
                </button>
                <button
                  type="button"
                  onClick={() => void setStatus(candidate, 'rejected')}
                  disabled={candidate.status === 'rejected'}
                >
                  Reject
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
