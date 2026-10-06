<template>
  <div class="login-container">
    <el-card class="login-card">
      <h2>语音日历登录</h2>
      <el-form :model="loginForm" label-width="80px">
        <el-form-item label="手机号">
          <el-input v-model="loginForm.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleLogin" style="width: 100%">登录</el-button>
        </el-form-item>
        <el-form-item>
          <router-link to="/register">没有账号？去注册</router-link>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../utils/request'
import { useUserStore } from '../store/user'

const router = useRouter()
const userStore = useUserStore()

const loginForm = ref({
  phone: '',
  password: ''
})

const handleLogin = async () => {
  try {
    const res = await request.post('/user/login', loginForm.value)
    // 保存Token和用户信息
    userStore.login(res.data.token, res.data.user)
    ElMessage.success('登录成功')
    router.push('/calendar')
  } catch (err) {
    console.error(err)
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f5f7fa;
}
.login-card {
  width: 400px;
  padding: 20px;
}
h2 {
  text-align: center;
  margin-bottom: 30px;
}
</style>