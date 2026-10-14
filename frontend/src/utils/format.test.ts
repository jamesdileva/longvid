import { describe, expect, it } from 'vitest';
import {
  formatDuration,
  formatFileSize,
  formatResolution,
  formatTimestamp,
  pluralize,
} from './format';

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

describe('formatDuration', () => {
  it('formats seconds as m:ss', () => {
    expect(formatDuration(95.4)).toBe('1:35');
    expect(formatDuration(5)).toBe('0:05');
  });

  it('formats hours as h:mm:ss', () => {
    expect(formatDuration(3600)).toBe('1:00:00');
    expect(formatDuration(3723)).toBe('1:02:03');
  });

  it('handles missing values', () => {
    expect(formatDuration(null)).toBe('—');
  });
});

describe('formatFileSize', () => {
  it('scales units', () => {
    expect(formatFileSize(512)).toBe('512 B');
    expect(formatFileSize(2048)).toBe('2 KB');
    expect(formatFileSize(2 * 1024 * 1024)).toBe('2 MB');
  });

  it('handles missing values', () => {
    expect(formatFileSize(null)).toBe('—');
  });
});

describe('formatResolution', () => {
  it('formats width by height', () => {
    expect(formatResolution(1920, 1080)).toBe('1920 × 1080');
  });

  it('handles missing values', () => {
    expect(formatResolution(null, null)).toBe('—');
  });
});
