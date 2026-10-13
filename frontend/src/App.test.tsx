import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import type { HealthResponse } from './api/health'

const healthy: HealthResponse = {
  status: 'ok',
  version: '0.1.0',
  service: 'retire-projection-api',
  database: { connected: true, latency_ms: 1.2, migration_revision: '0001' },
  timestamp: '2026-10-13T12:00:00+00:00',
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('App', () => {
  it('shows a loading state before the health request settles', () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}))
    render(<App />)
    expect(screen.getByTestId('loading')).toBeInTheDocument()
  })

  it('renders real health data returned by the API', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(healthy), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    render(<App />)
    expect(await screen.findByTestId('api-status')).toHaveTextContent('ok')
    expect(screen.getByTestId('db-status')).toHaveTextContent('connected')
    expect(screen.getByTestId('version')).toHaveTextContent('0.1.0')
    expect(screen.getByTestId('revision')).toHaveTextContent('0001')
  })

  it('shows an actionable error when the API is unreachable', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('network down'))
    render(<App />)
    const error = await screen.findByTestId('error')
    expect(error).toHaveTextContent(/could not reach the local api/i)
    expect(error).toHaveTextContent(/network down/)
  })
})
