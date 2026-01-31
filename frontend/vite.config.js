import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      // 代理所有 API 请求到后端
      '/auth': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/diaries': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/upload': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/ai': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/graph': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/spots': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/navigate': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: '../frontend-dist'
  }
})
