<template>
  <div class="register-container">
    <el-card class="register-card">
      <h2>语音日历注册</h2>
      <el-form :model="registerForm" label-width="80px">
        <el-form-item label="手机号">
          <el-input v-model="registerForm.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="registerForm.password" type="password" placeholder="请输入密码" />
        </el-form-item>
        <el-form-item label="验证码">
          <el-input v-model="registerForm.code" placeholder="请输入验证码" />
          <el-button @click="sendCode">发送验证码</el-button>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleRegister" style="width: 100%">注册</el-button>
        </el-form-item>
        <el-form-item>
          <router-link to="/login">已有账号？去登录</router-link>
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

const router = useRouter()

const registerForm = ref({
  phone: '',
  password: '',
  code: ''
})

const sendCode = async () => {
  // 调用后端发送验证码接口（如果有）
  try {
    await request.post('/user/send-code', { phone: registerForm.value.phone })
    ElMessage.success('验证码已发送')
  } catch (err) {
    console.error(err)
  }
}

const handleRegister = async () => {
  try {
    await request.post('/user/register', registerForm.value)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (err) {
    console.error(err)
  }
}
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f5f7fa;
}
.register-card {
  width: 400px;
  padding: 20px;
}
h2 {
  text-align: center;
  margin-bottom: 30px;
}
</style>