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

/** Human-readable singular/plural count. */
export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}
