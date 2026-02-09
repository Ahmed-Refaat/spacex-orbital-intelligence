import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
    dedupe: ['react', 'react-dom', 'scheduler'],
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'scheduler'],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Three.js and 3D visualization libs (keep react deps together)
          'three': ['three', '@react-three/fiber', '@react-three/drei'],
          // Charts library
          'charts': ['recharts'],
          // Core React libraries (keep all React deps in same chunk)
          'vendor': ['react', 'react-dom', 'scheduler', 'zustand', '@tanstack/react-query'],
          // Zod validation
          'validation': ['zod'],
        },
      },
    },
    chunkSizeWarningLimit: 1000, // Warn if chunk > 1MB
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8001',
        ws: true,
      },
    },
  },
})
