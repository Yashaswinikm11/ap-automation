import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 1000,
  },
  server: {
    port: 5173,
    proxy: {
      // Forward all /api/* calls to Django REST API
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Forward all /media/* calls so uploaded invoice files render in-browser
      '/media': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
