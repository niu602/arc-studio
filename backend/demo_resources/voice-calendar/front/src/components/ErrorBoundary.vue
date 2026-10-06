<template>
  <div v-if="hasError" class="error-boundary">
    <div class="error-content">
      <div class="error-icon">⚠️</div>
      <h2>页面加载失败</h2>
      <p>抱歉，应用出现了问题，请尝试刷新页面</p>
      <div class="error-actions">
        <button @click="reloadPage" class="btn-primary">刷新页面</button>
        <button @click="goHome" class="btn-secondary">返回首页</button>
      </div>
      <div v-if="errorDetails" class="error-details">
        <details>
          <summary>错误详情</summary>
          <pre>{{ errorDetails }}</pre>
        </details>
      </div>
    </div>
  </div>
  <slot v-else />
</template>

<script setup>
import { ref, onErrorCaptured } from 'vue'
import { useRouter } from 'vue-router'

const hasError = ref(false)
const errorDetails = ref('')
const router = useRouter()

// 捕获子组件错误
onErrorCaptured((err, instance, info) => {
  hasError.value = true
  errorDetails.value = `错误: ${err.message}\n组件: ${instance?.$options.name || '未知'}\n位置: ${info}`
  console.error('ErrorBoundary捕获错误:', err)
  return false
})

const reloadPage = () => {
  window.location.reload()
}

const goHome = () => {
  router.push('/')
  setTimeout(() => {
    hasError.value = false
  }, 100)
}
</script>

<style scoped>
.error-boundary {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 20px;
}

.error-content {
  text-align: center;
  max-width: 500px;
  background: white;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
}

.error-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.error-content h2 {
  color: #303133;
  margin-bottom: 10px;
  font-size: 24px;
}

.error-content p {
  color: #606266;
  margin-bottom: 30px;
  line-height: 1.6;
}

.error-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-bottom: 20px;
}

.btn-primary, .btn-secondary {
  padding: 10px 24px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s;
}

.btn-primary {
  background: #409eff;
  color: white;
}

.btn-primary:hover {
  background: #337ecc;
}

.btn-secondary {
  background: #f5f5f5;
  color: #606266;
  border: 1px solid #dcdfe6;
}

.btn-secondary:hover {
  background: #e4e7ed;
}

.error-details {
  margin-top: 20px;
  text-align: left;
}

.error-details summary {
  cursor: pointer;
  color: #409eff;
  font-size: 14px;
  margin-bottom: 10px;
  display: inline-block;
}

.error-details pre {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
  max-height: 200px;
  overflow: auto;
  text-align: left;
}
</style>