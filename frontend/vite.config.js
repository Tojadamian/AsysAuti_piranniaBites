import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    // proxy only /api requests to backend so Vite can serve the frontend root '/'
    proxy: {
      // proxy /api/* -> http://127.0.0.1:5000/api/* (bez usuwania prefiksu)
      '/api': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
        // nie usuwamy /api żeby backend widział pełną ścieżkę
        rewrite: (path) => path
      },
      // Proxy additional API endpoints to Flask backend
      '/data_dir': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
      '/participants': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
      '/participant': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
    }
  }
})
