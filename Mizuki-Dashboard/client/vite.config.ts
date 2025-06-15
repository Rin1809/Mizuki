import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Proxy cac request /api toi Vercel function router
      // hoac local express server (khi dev)
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
        // rewrite de goi toi 1 function duy nhat tren Vercel
        rewrite: (path) => path.replace(/^\/api/, '/api/stats'),
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});