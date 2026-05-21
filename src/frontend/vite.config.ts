import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const env = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env ?? {}
const frontendPort = Number(env.WEBGAL_FRONTEND_PORT || 5173)
const backendHost = env.WEBGAL_BACKEND_HOST || '127.0.0.1'
const backendPort = Number(env.WEBGAL_BACKEND_PORT || 8000)

export default defineConfig({
  plugins: [vue()],
  server: {
    port: frontendPort,
    proxy: {
      '/api': {
        target: `http://${backendHost}:${backendPort}`,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../webgal_agent/api/static',
    emptyOutDir: true,
  },
})
