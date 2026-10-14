import { useState } from 'react';

interface VideoImportFormProps {
  /** Runs the import for the returned path; resolves when finished. */
  onImport: (path: string) => Promise<void> | void;
}

export default function VideoImportForm({ onImport }: VideoImportFormProps) {
  const [path, setPath] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(candidate: string) {
    const trimmed = candidate.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    try {
      await onImport(trimmed);
      setPath('');
    } finally {
      setBusy(false);
    }
  }

  async function browse() {
    if (busy) return;
    const bridge = window.longvid;
    if (!bridge) return; // native dialog unavailable in plain browser dev
    const chosen = await bridge.chooseVideo();
    if (chosen) await submit(chosen);
  }

  return (
    <form
      className="video-import"
      onSubmit={(event) => {
        event.preventDefault();
        void submit(path);
      }}
    >
      <input
        aria-label="Video file path"
        placeholder="Video file path (or use Browse…)"
        value={path}
        onChange={(event) => setPath(event.target.value)}
      />
      <button type="button" onClick={() => void browse()} disabled={busy || !window.longvid}>
        Browse…
      </button>
      <button type="submit" disabled={busy || !path.trim()}>
        {busy ? 'Importing…' : 'Import video'}
      </button>
    </form>
  );
}
