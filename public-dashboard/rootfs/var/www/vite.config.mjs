import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Get base path from environment variable or use default
const basePath = process.env.VITE_BASE_PATH || '/'

// Get API URL from environment variable or use default
const apiUrl = process.env.VITE_API_URL || ''

export default defineConfig({
  plugins: [react()],
  base: basePath,
  define: {
    'import.meta.env.VITE_API_URL': JSON.stringify(apiUrl)
  },
  resolve: {
    conditions: ['module', 'browser', 'development|production']
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})
