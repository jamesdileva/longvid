import { useEffect, useMemo, useState } from 'react';
import { listEvents, listScenes } from '../services/analysis';
import type { AnalysisEvent, Scene } from '../types/analysis';
import { formatDuration } from '../utils/format';

interface AnalysisPanelProps {
  videoId: number;
  /** Seek the video preview to the given timestamp (seconds). */
  onSeek: (seconds: number) => void;
}

function countByType(events: AnalysisEvent[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const event of events) {
    counts.set(event.type, (counts.get(event.type) ?? 0) + 1);
  }
  return counts;
}

export default function AnalysisPanel({ videoId, onSeek }: AnalysisPanelProps) {
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [events, setEvents] = useState<AnalysisEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([listScenes(videoId), listEvents(videoId)])
      .then(([loadedScenes, loadedEvents]) => {
        if (!active) return;
        setScenes(loadedScenes);
        setEvents(loadedEvents);
        setError(null);
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : 'Failed to load analysis');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [videoId]);

  const typeCounts = useMemo(() => countByType(events), [events]);

  if (loading) return <p className="empty-note">Loading analysis…</p>;
  if (error) return <p className="empty-note">{error}</p>;

  return (
    <div className="analysis-panel" data-testid="analysis-panel">
      <div className="analysis-summary">
        <span data-testid="scene-count">{scenes.length} scenes</span>
        <span data-testid="event-count">{events.length} events</span>
        {[...typeCounts.entries()].map(([type, count]) => (
          <span className="status-pill" key={type}>
            {type.replace(/_/g, ' ')}: {count}
          </span>
        ))}
      </div>
      {scenes.length === 0 && events.length === 0 ? (
        <p className="empty-note">No analysis yet. Run Analyze to detect scenes and events.</p>
      ) : (
        <ol className="event-list" data-testid="event-list">
          {events.map((event) => (
            <li key={event.id}>
              <button
                type="button"
                className="event-row"
                onClick={() => onSeek(event.start_seconds)}
              >
                <span className="event-time">{formatDuration(event.start_seconds)}</span>
                <span className="event-type">{event.type.replace(/_/g, ' ')}</span>
                <span className="event-range">
                  {formatDuration(event.start_seconds)} – {formatDuration(event.end_seconds)}
                </span>
                {event.confidence !== null && (
                  <span className="event-confidence">
                    {Math.round(event.confidence * 100)}%
                  </span>
                )}
              </button>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
