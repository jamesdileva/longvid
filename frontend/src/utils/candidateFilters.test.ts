import { describe, expect, it } from 'vitest';
import {
  candidateDuration,
  filterCandidates,
  matchesFilter,
  sortCandidates,
} from './candidateFilters';
import type { Candidate } from '../types/candidate';

function candidate(overrides: Partial<Candidate> = {}): Candidate {
  return {
    id: 1,
    video_id: 7,
    start_seconds: 10,
    end_seconds: 20,
    status: 'pending',
    semantic_score: 0.5,
    audio_score: 0.5,
    visual_score: 0.5,
    context_score: 0.5,
    standalone_score: 0.5,
    novelty_score: 1,
    overall_score: 0.5,
    category: 'detected',
    reason: null,
    source: 'deterministic',
    event_ids: null,
    thumbnail_url: '/api/candidates/1/thumbnail',
    created_at: '2026-10-14T10:00:00',
    updated_at: '2026-10-14T10:00:00',
    ...overrides,
  };
}

describe('matchesFilter', () => {
  it('matches category synonyms case-insensitively', () => {
    expect(matchesFilter(candidate({ category: 'Hype Reaction' }), 'reaction')).toBe(true);
    expect(matchesFilter(candidate({ category: 'error moment' }), 'important')).toBe(true);
    expect(matchesFilter(candidate({ category: 'comedy bit' }), 'funny')).toBe(true);
    expect(matchesFilter(candidate({ category: 'high-energy play' }), 'high-energy')).toBe(true);
  });

  it('rejects non-matching categories and tolerates null', () => {
    expect(matchesFilter(candidate({ category: 'reaction' }), 'funny')).toBe(false);
    expect(matchesFilter(candidate({ category: null }), 'reaction')).toBe(false);
  });

  it('treats all and best as pass-through', () => {
    expect(matchesFilter(candidate({ category: null }), 'all')).toBe(true);
    expect(matchesFilter(candidate({ category: null }), 'best')).toBe(true);
  });
});

describe('filterCandidates', () => {
  it('keeps the top N by score for best', () => {
    const candidates = [0.9, 0.8, 0.7, 0.6].map((overall_score, index) =>
      candidate({ id: index + 1, overall_score }),
    );

    const best = filterCandidates(candidates, 'best', 2);

    expect(best.map((item) => item.id)).toEqual([1, 2]);
  });

  it('filters by category keyword', () => {
    const candidates = [
      candidate({ id: 1, category: 'funny' }),
      candidate({ id: 2, category: 'reaction' }),
    ];

    expect(filterCandidates(candidates, 'funny').map((item) => item.id)).toEqual([1]);
  });
});

describe('sortCandidates', () => {
  const a = candidate({ id: 1, overall_score: 0.5, start_seconds: 30, end_seconds: 70 });
  const b = candidate({ id: 2, overall_score: 0.9, start_seconds: 5, end_seconds: 25 });

  it('sorts by score descending', () => {
    expect(sortCandidates([a, b], 'score').map((item) => item.id)).toEqual([2, 1]);
  });

  it('sorts by timestamp ascending', () => {
    expect(sortCandidates([a, b], 'timestamp').map((item) => item.id)).toEqual([2, 1]);
  });

  it('sorts by duration descending', () => {
    expect(sortCandidates([a, b], 'duration').map((item) => item.id)).toEqual([1, 2]);
  });

  it('computes duration', () => {
    expect(candidateDuration(a)).toBe(40);
  });
});
