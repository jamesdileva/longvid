import { useState } from 'react';
import { assetUrl } from '../services/videos';

interface CandidateThumbProps {
  thumbnailUrl: string;
  alt: string;
}

/** Candidate start-frame preview with a graceful placeholder on load failure. */
export default function CandidateThumb({ thumbnailUrl, alt }: CandidateThumbProps) {
  const [failed, setFailed] = useState(false);
  const src = assetUrl(thumbnailUrl);
  if (!src || failed) {
    return <div className="candidate-thumb placeholder" aria-hidden="true" />;
  }
  return (
    <img
      className="candidate-thumb"
      data-testid="candidate-thumb"
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}
