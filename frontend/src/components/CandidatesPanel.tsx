import { useEffect, useMemo, useState } from 'react';
import { listProjectCandidates, updateCandidateStatus } from '../services/candidates';
import { assetUrl } from '../services/videos';
import CandidatePreview from './CandidatePreview';
import CandidateThumb from './CandidateThumb';
import type { Candidate, CandidateStatus } from '../types/candidate';
import {
  CANDIDATE_FILTERS,
  CANDIDATE_SORTS,
  candidateDuration,
  filterCandidates,
  sortCandidates,
  type CandidateFilter,
  type CandidateSort,
} from '../utils/candidateFilters';
import { formatDuration } from '../utils/format';

interface CandidateVideo {
  id: number;
  filename: string;
  preview_url: string | null;
}

interface CandidatesPanelProps {
  projectId: string;
  videos: CandidateVideo[];
  onSeekVideo: (videoId: number, seconds: number) => void;
}

export default function CandidatesPanel({ projectId, videos, onSeekVideo }: CandidatesPanelProps) {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<CandidateFilter>('all');
  const [sort, setSort] = useState<CandidateSort>('score');
  const [previewId, setPreviewId] = useState<number | null>(null);

  const filenameById = useMemo(
    () => new Map(videos.map((video) => [video.id, video.filename])),
    [videos],
  );
  const previewById = useMemo(
    () => new Map(videos.map((video) => [video.id, assetUrl(video.preview_url)])),
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

  const visible = useMemo(
    () => sortCandidates(filterCandidates(candidates, filter), sort),
    [candidates, filter, sort],
  );

  async function setStatus(candidate: Candidate, status: CandidateStatus) {
    try {
      const updated = await updateCandidateStatus(candidate.id, status);
      setCandidates((current) => current.map((item) => (item.id === updated.id ? updated : item)));
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

  if (candidates.length === 0) {
    return (
      <div className="candidates-panel" data-testid="candidates-panel">
        <p className="empty-note" data-testid="candidates-empty">
          No candidates yet. Use “Detect highlights” on a video to find clip-worthy moments.
        </p>
      </div>
    );
  }

  return (
    <div className="candidates-panel" data-testid="candidates-panel">
      <div className="candidate-toolbar">
        <div className="candidate-filters" role="group" aria-label="Filter candidates">
          {CANDIDATE_FILTERS.map((option) => (
            <button
              key={option.key}
              type="button"
              className={`filter-chip${filter === option.key ? ' active' : ''}`}
              aria-pressed={filter === option.key}
              onClick={() => setFilter(option.key)}
            >
              {option.label}
            </button>
          ))}
        </div>
        <label className="candidate-sort">
          Sort by
          <select
            value={sort}
            aria-label="Sort candidates"
            onChange={(event) => setSort(event.target.value as CandidateSort)}
          >
            {CANDIDATE_SORTS.map((option) => (
              <option key={option.key} value={option.key}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {visible.length === 0 ? (
        <p className="empty-note" data-testid="candidates-filtered-empty">
          No candidates match this filter.
        </p>
      ) : (
        <ul className="candidate-list" data-testid="candidate-list">
          {visible.map((candidate) => {
            const previewSrc = previewById.get(candidate.video_id) ?? null;
            return (
              <li className="candidate-card" key={candidate.id} data-testid="candidate-card">
                <CandidateThumb
                  thumbnailUrl={candidate.thumbnail_url}
                  alt={`Candidate at ${formatDuration(candidate.start_seconds)}`}
                />
                <div className="candidate-body">
                  <div className="card-header">
                    <span className="candidate-score" data-testid="candidate-score">
                      {Math.round(candidate.overall_score * 100)}
                    </span>
                    <span className="candidate-meta">
                      <span className="candidate-category">{candidate.category ?? 'detected'}</span>
                      <span className="candidate-source">{candidate.source}</span>
                      <span className={`status-pill ${candidate.status}`}>{candidate.status}</span>
                    </span>
                  </div>
                  <p className="candidate-title">{candidate.reason}</p>
                  <p className="candidate-times">
                    <button
                      type="button"
                      className="link-button"
                      onClick={() => onSeekVideo(candidate.video_id, candidate.start_seconds)}
                    >
                      {formatDuration(candidate.start_seconds)} –{' '}
                      {formatDuration(candidate.end_seconds)}
                    </button>
                    <span className="candidate-duration">
                      ({formatDuration(candidateDuration(candidate))})
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
                      onClick={() => setPreviewId(previewId === candidate.id ? null : candidate.id)}
                      disabled={!previewSrc}
                    >
                      {previewId === candidate.id ? 'Close preview' : 'Preview'}
                    </button>
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
                  {previewId === candidate.id && previewSrc && (
                    <CandidatePreview
                      src={previewSrc}
                      startSeconds={candidate.start_seconds}
                      endSeconds={candidate.end_seconds}
                    />
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
