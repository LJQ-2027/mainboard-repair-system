import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      // 开发时代理 API 请求到后端
      '/api': 'http://localhost:8899',
      '/health': 'http://localhost:8899',
      '/data': 'http://localhost:8899',
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
