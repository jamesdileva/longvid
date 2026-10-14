/**
 * Formatting helpers. Timestamps come from the backend as naive UTC ISO
 * strings; everything is rendered in UTC so output is deterministic.
 */

const DATE_TIME_FORMAT = new Intl.DateTimeFormat('en-US', {
  dateStyle: 'medium',
  timeStyle: 'short',
  timeZone: 'UTC',
});

function parseIsoUtc(iso: string): Date {
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(iso);
  const date = new Date(hasZone ? iso : `${iso}Z`);
  if (Number.isNaN(date.getTime())) {
    throw new Error(`Invalid timestamp: ${iso}`);
  }
  return date;
}

/** e.g. 2026-10-13T14:32:00 -> "Oct 13, 2026, 2:32 PM" (always UTC). */
export function formatTimestamp(iso: string): string {
  return DATE_TIME_FORMAT.format(parseIsoUtc(iso));
}

/** e.g. 95.4 -> "1:35", 3723 -> "1:02:03". Null-safe. */
export function formatDuration(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds) || seconds < 0) return '—';
  const total = Math.round(seconds);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  const pad = (value: number) => String(value).padStart(2, '0');
  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(secs)}` : `${minutes}:${pad(secs)}`;
}

/** e.g. 2097152 -> "2.0 MB". Null-safe. */
export function formatFileSize(bytes: number | null): string {
  if (bytes === null || !Number.isFinite(bytes) || bytes < 0) return '—';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const rounded = unit === 0 ? Math.round(value) : Math.round(value * 10) / 10;
  return `${rounded} ${units[unit]}`;
}

/** e.g. (1920, 1080) -> "1920 × 1080" */
export function formatResolution(width: number | null, height: number | null): string {
  if (!width || !height) return '—';
  return `${width} × ${height}`;
}

/** Human-readable singular/plural count. */
export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}
