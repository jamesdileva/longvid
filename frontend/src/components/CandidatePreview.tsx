import { useEffect, useRef, useState } from 'react';
import { formatDuration } from '../utils/format';

interface CandidatePreviewProps {
  src: string;
  startSeconds: number;
  endSeconds: number;
}

/** Minimal in-range player: play/pause, scrub, and stop at the clip end. */
export default function CandidatePreview({ src, startSeconds, endSeconds }: CandidatePreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [position, setPosition] = useState(startSeconds);

  useEffect(() => {
    const element = videoRef.current;
    if (!element) return;
    element.currentTime = startSeconds;
    setPosition(startSeconds);
    setPlaying(false);
  }, [src, startSeconds]);

  function safePlay(element: HTMLVideoElement) {
    const result = element.play();
    if (result && typeof result.catch === 'function') {
      result.catch(() => undefined);
    }
  }

  function togglePlay() {
    const element = videoRef.current;
    if (!element) return;
    if (playing) {
      element.pause();
      setPlaying(false);
      return;
    }
    if (element.currentTime < startSeconds || element.currentTime >= endSeconds) {
      element.currentTime = startSeconds;
    }
    safePlay(element);
    setPlaying(true);
  }

  function handleTimeUpdate() {
    const element = videoRef.current;
    if (!element) return;
    if (element.currentTime >= endSeconds) {
      element.pause();
      element.currentTime = endSeconds;
      setPosition(endSeconds);
      setPlaying(false);
      return;
    }
    setPosition(element.currentTime);
  }

  function handleSeek(event: React.ChangeEvent<HTMLInputElement>) {
    const value = Number(event.target.value);
    const element = videoRef.current;
    if (element) element.currentTime = value;
    setPosition(value);
  }

  return (
    <div className="candidate-preview" data-testid="candidate-preview">
      <video
        ref={videoRef}
        className="candidate-preview-video"
        src={src}
        preload="metadata"
        onTimeUpdate={handleTimeUpdate}
        onEnded={() => setPlaying(false)}
      />
      <div className="preview-controls">
        <button type="button" onClick={togglePlay}>
          {playing ? 'Pause' : 'Play'}
        </button>
        <input
          type="range"
          min={startSeconds}
          max={endSeconds}
          step={0.1}
          value={position}
          onChange={handleSeek}
          aria-label="Seek"
          data-testid="preview-seek"
        />
        <span className="preview-time" data-testid="preview-time">
          {formatDuration(position)} / {formatDuration(endSeconds)}
        </span>
      </div>
    </div>
  );
}
