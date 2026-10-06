import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    // 1. 前端端口改回 5173（Vite默认端口，和后端8888区分开）
    port: 5173,
    open: true,
    // 2. 关键：配置接口代理，转发前端请求到后端
    proxy: {
      '/api': {
        target: 'http://localhost:8888', // 后端运行地址
        changeOrigin: true,              // 开启跨域
        rewrite: (path) => path          // 保留/api前缀（和后端接口匹配）
      }
    }
  }
})