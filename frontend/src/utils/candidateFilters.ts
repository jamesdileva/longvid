/**
 * Pure filtering and sorting for the candidate browser (roadmap 8.3).
 *
 * Category filters match the free-form category text returned by the LLM
 * against keyword groups, so "error moment" still surfaces under Important
 * and "hype reaction" under Reaction.
 */

import type { Candidate } from '../types/candidate';

export type CandidateFilter = 'all' | 'best' | 'funny' | 'reaction' | 'important' | 'high-energy';
export type CandidateSort = 'score' | 'timestamp' | 'duration';

export const CANDIDATE_FILTERS: { key: CandidateFilter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'best', label: 'Best' },
  { key: 'funny', label: 'Funny' },
  { key: 'reaction', label: 'Reaction' },
  { key: 'important', label: 'Important' },
  { key: 'high-energy', label: 'High Energy' },
];

export const CANDIDATE_SORTS: { key: CandidateSort; label: string }[] = [
  { key: 'score', label: 'Score' },
  { key: 'timestamp', label: 'Timestamp' },
  { key: 'duration', label: 'Duration' },
];

/** How many top-scoring candidates the "Best" filter keeps. */
export const BEST_COUNT = 5;

const CATEGORY_KEYWORDS: Record<'funny' | 'reaction' | 'important' | 'high-energy', string[]> = {
  funny: ['funny', 'humor', 'humour', 'comedy', 'joke', 'laugh', 'meme'],
  reaction: ['reaction', 'react', 'surprise', 'shock', 'awe', 'wow'],
  important: ['important', 'highlight', 'key', 'insight', 'informative', 'announcement', 'error'],
  'high-energy': ['high energy', 'high-energy', 'energy', 'hype', 'intense', 'exciting', 'climax'],
};

export function candidateDuration(candidate: Candidate): number {
  return candidate.end_seconds - candidate.start_seconds;
}

export function matchesFilter(candidate: Candidate, filter: CandidateFilter): boolean {
  if (filter === 'all' || filter === 'best') return true;
  const category = (candidate.category ?? '').toLowerCase();
  return CATEGORY_KEYWORDS[filter].some((keyword) => category.includes(keyword));
}

/** Apply the active filter. "Best" keeps the top BEST_COUNT by overall score. */
export function filterCandidates(
  candidates: Candidate[],
  filter: CandidateFilter,
  bestCount: number = BEST_COUNT,
): Candidate[] {
  if (filter === 'best') {
    const bestIds = new Set(
      [...candidates]
        .sort((a, b) => b.overall_score - a.overall_score)
        .slice(0, bestCount)
        .map((candidate) => candidate.id),
    );
    return candidates.filter((candidate) => bestIds.has(candidate.id));
  }
  return candidates.filter((candidate) => matchesFilter(candidate, filter));
}

/** Stable sort: score desc, timestamp asc, duration desc. */
export function sortCandidates(candidates: Candidate[], sort: CandidateSort): Candidate[] {
  const sorted = [...candidates];
  switch (sort) {
    case 'timestamp':
      sorted.sort((a, b) => a.start_seconds - b.start_seconds);
      break;
    case 'duration':
      sorted.sort((a, b) => candidateDuration(b) - candidateDuration(a));
      break;
    default:
      sorted.sort((a, b) => b.overall_score - a.overall_score);
  }
  return sorted;
}
