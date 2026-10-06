import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // cytoscape / cytoscape-dagre ship CommonJS; Vite handles it via optimizeDeps.
  optimizeDeps: {
    include: ['cytoscape', 'cytoscape-dagre', 'dagre'],
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
