/**
 * API location configuration. The backend is always a local service —
 * never point this at a remote host (docs/architecture.md §23).
 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8790/api';

/** Origin portion used to build asset URLs from backend-relative paths. */
export const API_ORIGIN = API_BASE_URL.replace(/\/api\/?$/, '');
