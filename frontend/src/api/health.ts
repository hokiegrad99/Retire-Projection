/** Shape of GET /api/health — keep in sync with backend/app/routers/health.py */
export interface HealthResponse {
  status: 'ok' | 'degraded'
  version: string
  service: string
  database: {
    connected: boolean
    latency_ms: number | null
    migration_revision: string | null
  }
  timestamp: string
}

/**
 * Fetch service health from the local API.
 *
 * 200 = healthy, 503 = database unreachable (body still JSON).
 * Any other status, a network failure, or invalid JSON rejects.
 */
export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch('/api/health')
  if (!response.ok && response.status !== 503) {
    throw new Error(`Unexpected health status ${response.status}`)
  }
  return (await response.json()) as HealthResponse
}
