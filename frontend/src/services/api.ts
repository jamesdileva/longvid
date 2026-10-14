import type { HealthResponse } from '../types/health';
import { apiRequest } from './http';

/** Probe backend availability. Components must not call fetch directly. */
export async function fetchHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>('/health');
}
