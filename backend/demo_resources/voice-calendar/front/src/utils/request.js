import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../store/user'
import router from '../router' // 引入路由，用于401重定向
import { getActivePinia } from 'pinia' // 引入Pinia工具函数

// 创建axios实例
const request = axios.create({
  baseURL: '/api', // 对应vite.config.js的代理
  timeout: 10000,
  withCredentials: true // 允许携带Cookie（根据后端需求调整）
})

// 存储正在请求的接口，防止重复请求
const pendingRequests = new Map()

// 请求拦截器：自动添加Token（修复Pinia使用时机）
request.interceptors.request.use(
  config => {
    // 1. 防重复请求：生成请求唯一标识
    const requestKey = `${config.method}-${config.url}`
    if (pendingRequests.has(requestKey)) {
      // 取消重复请求
      pendingRequests.get(requestKey).cancel('重复请求已取消')
    }
    // 创建取消令牌
    const source = axios.CancelToken.source()
    config.cancelToken = source.token
    pendingRequests.set(requestKey, source)

    // 2. 动态获取Pinia store（关键修复）
    const pinia = getActivePinia()
    if (pinia) {
      const userStore = useUserStore(pinia)
      if (userStore.token) {
        config.headers.Authorization = `Bearer ${userStore.token}`
      }
    }

    return config
  },
  error => {
    // 移除取消的请求
    const requestKey = `${error.config.method}-${error.config.url}`
    pendingRequests.delete(requestKey)
    return Promise.reject(error)
  }
)

// 响应拦截器：完善错误处理
request.interceptors.response.use(
  response => {
    // 移除已完成的请求
    const requestKey = `${response.config.method}-${response.config.url}`
    pendingRequests.delete(requestKey)

    const res = response.data
    // 1. 处理业务错误（非200状态码）
    if (res.code !== 200) {
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || '请求失败'))
    }
    return res
  },
  error => {
    // 移除已完成的请求
    if (error.config) {
      const requestKey = `${error.config.method}-${error.config.url}`
      pendingRequests.delete(requestKey)
    }

    // 2. 处理不同类型的错误（关键修复）
    if (axios.isCancel(error)) {
      // 处理取消请求
      console.log('请求已取消:', error.message)
      return Promise.reject(error)
    } else if (error.response) {
      // 2.1 有响应但状态码异常
      const { status, data } = error.response
      switch (status) {
        case 401:
          // 处理未授权：清除token并跳转登录页
          const pinia = getActivePinia()
          if (pinia) {
            const userStore = useUserStore(pinia)
            userStore.logout() // 假设你有退出登录的action
          }
          ElMessage.error(data.message || '登录状态已过期，请重新登录')
          router.push('/login')
          break
        case 404:
          ElMessage.error('请求资源不存在')
          break
        case 500:
          ElMessage.error(data.message || '服务器内部错误')
          break
        case 502:
          ElMessage.error('网关错误，请稍后重试')
          break
        case 504:
          ElMessage.error('请求超时，请稍后重试')
          break
        default:
          ElMessage.error(data.message || `请求失败：${status}`)
      }
    } else if (error.request) {
      // 2.2 请求已发出但无响应（网络错误/超时）
      ElMessage.error('网络异常，请检查网络连接')
    } else {
      // 2.3 请求配置错误
      ElMessage.error('请求配置错误：' + error.message)
    }

    return Promise.reject(error)
  }
)

export default request