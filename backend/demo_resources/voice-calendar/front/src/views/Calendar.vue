<template>
  <div class="calendar-container">
    <div class="header">
      <h2>我的日程</h2>
      <el-button @click="handleLogout" type="danger">退出登录</el-button>
    </div>
    <FullCalendar
        ref="calendarRef"
        :options="calendarOptions"
        class="calendar-content"
    />

    <!-- 语音添加日程按钮 → 点击开始/点击结束模式 -->
    <div class="voice-btn-wrapper">
      <el-button
          type="primary"
          circle
          size="large"
          :class="{ recording: isRecording }"
          @click="toggleRecord"
      >
        {{ isRecording ? '■' : '●' }}
      </el-button>
      <span class="tip">{{ isRecording ? '再次点击结束录音' : '点击开始录音' }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import request from '../utils/request'
import { useUserStore } from '../store/user'

const router = useRouter()
const userStore = useUserStore()
const calendarRef = ref(null)
const isRecording = ref(false)

// 语音合成播报函数：给用户语音反馈
const speak = (text) => {
  // 先停止之前正在播放的语音，避免重叠
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text)
  // 设置中文语音
  utterance.lang = 'zh-CN'
  // 语速设置为0.9，更清晰自然
  utterance.rate = 0.9
  // 音量最大
  utterance.volume = 1
  // 开始播报
  window.speechSynthesis.speak(utterance)
}

// 全局变量（每次录音前后都会安全重置）
let audioContext = null
let mediaStream = null
let audioProcessor = null
let audioData = []

// 日历配置
const calendarOptions = ref({
  plugins: [dayGridPlugin, interactionPlugin],
  initialView: 'dayGridMonth',
  events: [],
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: ''
  },
  height: 'auto'
})

// 加载用户日程
const loadSchedules = async () => {
  try {
    const today = new Date()
    const startDate = today.toISOString().split('T')[0]
    const endDate = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]

    const res = await request.get('/schedule/list', {
      params: { startDate, endDate }
    })

    calendarOptions.value.events = res.data.map(schedule => ({
      id: schedule.id,
      title: schedule.title,
      start: schedule.startTime,
      end: schedule.endTime,
      color: '#409EFF'
    }))
    console.log('日程加载成功', res.data)
  } catch (err) {
    console.error('加载日程失败', err)
    ElMessage.error('加载日程失败')
  }
}

// 退出登录
const handleLogout = () => {
  window.speechSynthesis.cancel()
  userStore.logout()
  ElMessage.success('已退出登录')
  speak('已退出登录')
  router.push('/login')
}

// 手动实现WAV编码
const float32ToWav = (samples, sampleRate) => {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)

  const writeString = (offset, string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i))
    }
  }

  writeString(0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeString(36, 'data')
  view.setUint32(40, samples.length * 2, true)

  let offset = 44
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true)
    offset += 2
  }

  return buffer
}

// 安全清理所有录音资源
const cleanUpResources = async () => {
  console.log('【前端】开始安全清理资源')
  // 1. 停止音频处理器
  if (audioProcessor) {
    try {
      audioProcessor.disconnect()
      console.log('【前端】音频处理器已断开')
    } catch (e) {
      console.warn('【前端】音频处理器断开失败（可能已断开）', e)
    }
    audioProcessor = null
  }

  // 2. 停止媒体流
  if (mediaStream) {
    try {
      mediaStream.getTracks().forEach(track => track.stop())
      console.log('【前端】媒体流已停止')
    } catch (e) {
      console.warn('【前端】媒体流停止失败', e)
    }
    mediaStream = null
  }

  // 3. 关闭音频上下文
  if (audioContext) {
    try {
      await audioContext.close()
      console.log('【前端】音频上下文已关闭')
    } catch (e) {
      console.warn('【前端】音频上下文关闭失败', e)
    }
    audioContext = null
  }

  console.log('【前端】资源清理完成')
}

// 切换录音状态（点击一次开始，再点击一次结束）
const toggleRecord = async () => {
  console.log('【前端】触发toggleRecord，当前状态：', isRecording.value)

  if (!isRecording.value) {
    // 开始录音：先清理旧资源，避免冲突
    await cleanUpResources()

    console.log('【前端】开始执行startRecord')
    try {
      console.log('【前端】请求麦克风权限...')
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
      console.log('【前端】麦克风权限获取成功！')

      // 1. 创建音频上下文，强制16000Hz采样率（百度要求）
      audioContext = new AudioContext({ sampleRate: 16000 })
      // 关键修复：启动音频上下文，避免挂起状态
      await audioContext.resume()
      console.log('【前端】音频上下文已启动')

      const source = audioContext.createMediaStreamSource(mediaStream)
      audioProcessor = audioContext.createScriptProcessor(4096, 1, 1)
      audioData = []

      // 关键修复：先设置录音状态为true，再连接处理器，避免数据被忽略
      isRecording.value = true
      console.log('【前端】录音状态已设为true')

      audioProcessor.onaudioprocess = (e) => {
        const channelData = e.inputBuffer.getChannelData(0)
        audioData.push(new Float32Array(channelData))
        console.log('【前端】收到音频数据', channelData.length)
      }

      source.connect(audioProcessor)
      audioProcessor.connect(audioContext.destination)

      // 停止之前的语音播报
      window.speechSynthesis.cancel()
      ElMessage.success('开始录音，请说话…')
      speak('开始录音，请说话')
      console.log('【前端】录音开始，等待用户说话...')

    } catch (e) {
      console.error('【前端】麦克风访问失败', e)
      ElMessage.error('麦克风访问失败：' + (e?.message || '未知错误'))
      await cleanUpResources()
    }
  } else {
    // 结束录音并上传
    console.log('【前端】开始执行stopRecord')
    isRecording.value = false
    ElMessage.info('正在识别语音...')
    speak('正在识别语音')

    try {
      console.log('【前端】停止采集音频')
      // 先断开处理器，再合并数据
      if (audioProcessor) {
        audioProcessor.disconnect()
        audioProcessor = null
      }

      // 关键修复：先合并数据，再清理资源，确保audioData不被影响
      console.log('【前端】合并音频数据')
      if (audioData.length === 0) {
        throw new Error('未采集到音频数据，请重新录音')
      }

      const totalLength = audioData.reduce((sum, buf) => sum + buf.length, 0)
      const mergedData = new Float32Array(totalLength)
      let offset = 0
      for (const buf of audioData) {
        mergedData.set(buf, offset)
        offset += buf.length
      }

      console.log('【前端】编码成WAV文件')
      const wavBuffer = float32ToWav(mergedData, 16000)
      const blob = new Blob([wavBuffer], { type: 'audio/wav' })
      console.log('【前端】生成的音频文件大小', blob.size, '字节')

      const formData = new FormData()
      formData.append('file', blob, 'voice.wav')

      console.log('【前端】开始上传到后端 /api/voice/command')
      // ============== 核心修改 1 ==============
      // 去掉 blob，改为请求JSON，延长超时时间
      const response = await request.post('/voice/command', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 30000
      })

      console.log('【前端】上传成功，收到后端响应')
      // ============== 核心修改 2 ==============
      // 直接读取JSON响应体
      const { commandType, message } = response.data
      console.log('【前端】指令类型：', commandType, '指令内容：', message)

      // ============== 核心修改 3 ==============
      // 删除无用的音频播放代码
      if (commandType === 'add' || commandType === 'delete') {
        ElMessage.success(message)
        speak(message)
        loadSchedules() // 刷新日历
      } else {
        ElMessage.info(message)
        speak(message)
      }

    } catch (e) {
      console.error('【前端】上传失败', e)
      const errorMsg = '识别失败：' + (e?.message || '未知错误')
      ElMessage.error(errorMsg)
      speak(errorMsg)
    } finally {
      // 关键修复：最后再清理资源，确保数据处理完成
      await cleanUpResources()
      audioData = [] // 重置数据，避免影响下一次录音
    }
  }
}

onMounted(() => {
  console.log('【前端】Calendar组件挂载完成')
  loadSchedules()
})

onUnmounted(() => {
  // 组件卸载时停止语音播报，避免离开页面后继续播放
  window.speechSynthesis.cancel()
})
</script>

<style scoped>
/* 全局重置，让日历全屏 */
.calendar-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  overflow: hidden;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  margin: 0;
  background: #fff;
  border-bottom: 1px solid #eee;
}

/* 日历容器占满剩余高度，电脑上全屏显示 */
.calendar-content {
  flex: 1;
  padding: 0 16px 16px;
  height: calc(100vh - 80px); /* 减去header高度 */
}

/* 日历内容自适应，不会被截断 */
.calendar-content >>> .fc {
  height: 100% !important;
}

.calendar-content >>> .fc-view-harness {
  height: 100% !important;
}

/* 语音按钮样式 */
.voice-btn-wrapper {
  position: fixed;
  right: 30px;
  bottom: 30px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  z-index: 999;
}

.voice-btn-wrapper button {
  width: 60px;
  height: 60px;
  font-size: 24px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
}

.voice-btn-wrapper button.recording {
  background-color: #f56c6c !important;
  box-shadow: 0 0 20px rgba(245, 108, 108, 0.5);
  transform: scale(1.1);
}

.voice-btn-wrapper .tip {
  font-size: 12px;
  color: #666;
}
</style>