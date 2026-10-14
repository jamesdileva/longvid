/** Base URL of the local LongVid API. Never point this at a remote host. */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8790/api';

/** Shared JSON request helper. All API traffic funnels through here. */
export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    let detail = `${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    } catch {
      // Non-JSON error body; status alone is enough.
    }
    throw new Error(`Request to ${path} failed: ${detail}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
