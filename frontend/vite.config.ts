import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Three.js and 3D visualization libs
          'three': ['three', '@react-three/fiber', '@react-three/drei'],
          // Charts library
          'charts': ['recharts'],
          // Core React libraries
          'vendor': ['react', 'react-dom', 'zustand', '@tanstack/react-query'],
          // Zod validation
          'validation': ['zod'],
        },
      },
    },
    chunkSizeWarningLimit: 600, // Warn if chunk > 600KB
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
