import { useEffect, useState } from 'react'
import { getHealth, type HealthResponse } from './api/health'

type LoadState =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; health: HealthResponse }

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="card">
      <h2>{title}</h2>
      {children}
    </section>
  )
}

export default function App() {
  const [state, setState] = useState<LoadState>({ kind: 'loading' })

  useEffect(() => {
    let cancelled = false
    getHealth()
      .then((health) => {
        if (!cancelled) setState({ kind: 'ready', health })
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({
            kind: 'error',
            message: error instanceof Error ? error.message : String(error),
          })
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main className="container">
      <header>
        <h1>Retire Projection</h1>
        <p className="subtitle">Local-first retirement planning</p>
      </header>

      {state.kind === 'loading' && (
        <p data-testid="loading" role="status">
          Loading service status…
        </p>
      )}

      {state.kind === 'error' && (
        <Card title="API unreachable">
          <p data-testid="error" className="error">
            Could not reach the local API: {state.message}. Is the backend
            running? See OPERATIONS.md.
          </p>
        </Card>
      )}

      {state.kind === 'ready' && (
        <>
          <Card title="Service status">
            <dl className="status-grid">
              <dt>API</dt>
              <dd data-testid="api-status">{state.health.status}</dd>
              <dt>Database</dt>
              <dd data-testid="db-status">
                {state.health.database.connected ? 'connected' : 'unreachable'}
              </dd>
              <dt>Version</dt>
              <dd data-testid="version">{state.health.version}</dd>
              <dt>Schema revision</dt>
              <dd data-testid="revision">
                {state.health.database.migration_revision ?? 'none'}
              </dd>
              <dt>DB latency</dt>
              <dd data-testid="latency">
                {state.health.database.latency_ms === null
                  ? 'n/a'
                  : `${state.health.database.latency_ms} ms`}
              </dd>
            </dl>
          </Card>
          <Card title="Coming soon">
            <p className="muted">
              Net worth dashboard, projections, scenarios and simulations arrive
              with Phase 1 — this screen only reports real health data from the
              running service.
            </p>
          </Card>
        </>
      )}
    </main>
  )
}
