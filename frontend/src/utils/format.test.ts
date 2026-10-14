import { describe, expect, it } from 'vitest';
import { formatTimestamp, pluralize } from './format';

describe('formatTimestamp', () => {
  it('formats a naive UTC timestamp deterministically', () => {
    expect(formatTimestamp('2026-10-13T14:32:00')).toBe('Oct 13, 2026, 2:32 PM');
  });

  it('accepts timestamps that already carry a zone', () => {
    expect(formatTimestamp('2026-01-01T00:00:00Z')).toBe('Jan 1, 2026, 12:00 AM');
  });

  it('rejects garbage', () => {
    expect(() => formatTimestamp('not-a-date')).toThrow('Invalid timestamp');
  });
});

describe('pluralize', () => {
  it('uses the singular form for one', () => {
    expect(pluralize(1, 'video')).toBe('1 video');
  });

  it('uses the plural form otherwise', () => {
    expect(pluralize(0, 'video')).toBe('0 videos');
    expect(pluralize(3, 'clip')).toBe('3 clips');
  });
});
