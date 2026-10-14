/** Backend contract types (mirror of backend Pydantic schemas). */

export interface HealthResponse {
  status: string;
  version: string;
  database: string;
}
