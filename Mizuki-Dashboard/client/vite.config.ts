import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path'; // << them dong nay

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
    },
  },
  // them doan resolve.alias
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});