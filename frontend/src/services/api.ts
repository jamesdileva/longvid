import type { HealthResponse } from '../types/health';

/** Base URL of the local LongVid API. Never point this at a remote host. */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8790/api';

/** Probe backend availability. Components must not call fetch directly. */
export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`);
  }
  return (await response.json()) as HealthResponse;
}
