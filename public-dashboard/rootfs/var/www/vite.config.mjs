import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// For Home Assistant ingress, use relative paths
// This ensures assets work correctly with the ingress proxy system
export default defineConfig({
  plugins: [react()],
  base: './',  // Use relative paths for all assets
  define: {
    'import.meta.env.VITE_API_URL': JSON.stringify('')  // Use relative API paths
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
    sourcemap: true,
    rollupOptions: {
      output: {
        // Ensure all asset references use relative paths
        assetFileNames: 'assets/[name]-[hash][extname]',
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
      }
    }
  }
})
