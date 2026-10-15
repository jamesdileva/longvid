import { useEffect, useState } from 'react';
import { getTranscript } from '../services/transcripts';
import type { Transcript } from '../types/transcript';
import { formatDuration } from '../utils/format';

interface TranscriptViewerProps {
  videoId: number;
  /** Seek the video preview to the given timestamp (seconds). */
  onSeek: (seconds: number) => void;
}

export default function TranscriptViewer({ videoId, onSeek }: TranscriptViewerProps) {
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getTranscript(videoId)
      .then((loaded) => {
        if (active) {
          setTranscript(loaded);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : 'Failed to load transcript');
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [videoId]);

  if (loading) return <p className="empty-note">Loading transcript…</p>;

  if (error) {
    return <p className="empty-note">{error.includes('No transcript') ? 'No transcript yet. Run transcription to generate one.' : error}</p>;
  }

  if (!transcript || transcript.segments.length === 0) {
    return <p className="empty-note">Transcript is empty.</p>;
  }

  return (
    <ol className="transcript" data-testid="transcript">
      {transcript.segments.map((segment) => (
        <li key={segment.id}>
          <button
            type="button"
            className="transcript-line"
            onClick={() => onSeek(segment.start_seconds)}
          >
            <span className="transcript-time">{formatDuration(segment.start_seconds)}</span>
            <span className="transcript-text">{segment.text}</span>
          </button>
        </li>
      ))}
    </ol>
  );
}
