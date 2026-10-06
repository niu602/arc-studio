import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: '',
    userInfo: {}
  }),
  actions: {
    // 初始化：安全读取本地存储
    init() {
      // 安全读取token
      try {
        this.token = localStorage.getItem('token') || ''
      } catch (e) {
        this.token = ''
      }

      try {
        const userInfoStr = localStorage.getItem('userInfo')
        if (userInfoStr && userInfoStr !== 'undefined' && userInfoStr !== 'null') {
          this.userInfo = JSON.parse(userInfoStr)
        } else {
          this.userInfo = {}
        }
      } catch (e) {
        this.userInfo = {}
        // 清理损坏的数据
        localStorage.removeItem('userInfo')
      }
    },

    // 登录：保存Token和用户信息
    login(token, userInfo) {
      this.token = token
      this.userInfo = userInfo
      localStorage.setItem('token', token)
      localStorage.setItem('userInfo', JSON.stringify(userInfo))
    },

    // 登出：清空数据
    logout() {
      this.token = ''
      this.userInfo = {}
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
    }
  }
})