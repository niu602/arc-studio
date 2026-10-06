import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

// 主应用
import App from './App.vue'
import router from './router'
import { useUserStore } from './store/user'

// 创建应用实例
const app = createApp(App)
const pinia = createPinia()

// 使用插件
app.use(pinia)
// 初始化用户状态：从localStorage恢复登录信息，解决刷新后登录状态丢失问题
const userStore = useUserStore()
userStore.init()
app.use(router)
app.use(ElementPlus)

// 全局错误处理
app.config.errorHandler = (err, instance, info) => {
  console.error('Vue错误:', err)
  console.error('组件实例:', instance)
  console.error('错误信息:', info)
  
  // 可以在这里集成错误上报
  if (import.meta.env.PROD) {
    // 生产环境错误上报
  }
}

// 应用挂载成功后隐藏加载动画
const mountApp = () => {
  // 隐藏加载动画
  const loadingElement = document.getElementById('loading-screen')
  if (loadingElement) {
    loadingElement.classList.add('hidden')
    // 动画结束后移除元素
    setTimeout(() => {
      if (loadingElement.parentNode) {
        loadingElement.parentNode.removeChild(loadingElement)
      }
    }, 500)
  }
  
  console.log('🎉 语音日程管理系统启动成功！')
  console.log('环境:', import.meta.env.MODE)
  console.log('API地址:', import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080')
}

// 挂载应用
app.mount('#app')

// 延迟执行以确保DOM更新完成
setTimeout(mountApp, 100)