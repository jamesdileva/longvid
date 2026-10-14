import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import VideoImportForm from './VideoImportForm';

afterEach(() => {
  vi.restoreAllMocks();
  delete (window as { longvid?: unknown }).longvid;
});

describe('VideoImportForm', () => {
  it('submits the typed path', async () => {
    const onImport = vi.fn().mockResolvedValue(undefined);
    render(<VideoImportForm onImport={onImport} />);

    fireEvent.change(screen.getByLabelText('Video file path'), {
      target: { value: 'D:/clips/recording.mp4' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Import video' }));

    await waitFor(() => {
      expect(onImport).toHaveBeenCalledWith('D:/clips/recording.mp4');
    });
    // field clears after a successful import
    await waitFor(() => {
      expect(screen.getByLabelText('Video file path')).toHaveValue('');
    });
  });

  it('disables submit without a path', () => {
    render(<VideoImportForm onImport={vi.fn()} />);

    expect(screen.getByRole('button', { name: 'Import video' })).toBeDisabled();
  });

  it('uses the native dialog when the Electron bridge exists', async () => {
    const chooseVideo = vi.fn().mockResolvedValue('D:/clips/picked.mp4');
    (window as { longvid?: unknown }).longvid = { chooseVideo };
    const onImport = vi.fn().mockResolvedValue(undefined);

    render(<VideoImportForm onImport={onImport} />);
    fireEvent.click(screen.getByRole('button', { name: 'Browse…' }));

    await waitFor(() => {
      expect(chooseVideo).toHaveBeenCalled();
      expect(onImport).toHaveBeenCalledWith('D:/clips/picked.mp4');
    });
  });

  it('disables Browse without the Electron bridge', () => {
    render(<VideoImportForm onImport={vi.fn()} />);

    expect(screen.getByRole('button', { name: 'Browse…' })).toBeDisabled();
  });
});
