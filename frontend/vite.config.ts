import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// The API port comes from the project-root .env (same single source of
// truth the backend reads), so dev proxy and server can never drift apart.
export default defineConfig(({ mode }) => {
  const rootEnv = loadEnv(mode, '../', '')
  const apiPort = rootEnv.APP_PORT || '8000'

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': {
          target: `http://127.0.0.1:${apiPort}`,
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./vitest.setup.ts'],
      include: ['src/**/*.{test,spec}.{ts,tsx}'],
    },
  }
})
