<template>
  <div>
    <PortalNav />
    <div style="padding: 24px 40px; max-width: 1000px; margin: 0 auto">
      <h2>在线试用</h2>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
        title="填入 API Key 即可真实调用接口。没有 Key 请先点击「申请」注册（新注册赠送 100 点）。"
      />

      <el-card>
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap">
          <b>API Key：</b>
          <el-input
            v-model="apiKey"
            placeholder="粘贴你的 API Key"
            style="max-width: 420px"
            show-password
            @keyup.enter="saveKey"
          />
          <el-button type="primary" :loading="savingKey" @click="saveKey">保存</el-button>
          <el-button type="success" plain @click="$router.push('/register')">申请</el-button>
          <el-button v-if="apiKey" plain @click="copyKey">复制 Key</el-button>
          <el-button type="danger" plain @click="clearKey">清除本机 Key</el-button>
          <span v-if="keyInfo" style="font-size: 12px; color: #67c23a">
            Key 有效：{{ keyInfo.name }}（余额 {{ keyInfo.balance }} 点）
          </span>
          <span v-if="keyInfo" style="font-size: 12px; color: #909399">
            会员登录后自动带出本人 Key，退出登录即清除，不留存他人 Key
          </span>
        </div>
        <el-alert
          v-if="keyInfo && keyInfo.balance <= 0"
          type="error"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
          title="该 Key 余额为 0，AI 剪辑将被拒绝（402）。请登录客户控制台充值后再使用：请在控制台输入金额并扫码支付，或联系平台管理员。"
        >
          <template #default>
            <el-button size="small" type="primary" plain style="margin-top: 8px" @click="goRecharge">去客户控制台充值</el-button>
          </template>
        </el-alert>
        <el-alert
          v-else-if="keyInfo && keyInfo.balance <= 5"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
          :title="`该 Key 余额仅剩 ${keyInfo.balance} 点，请及时充值以免剪辑中断。`"
        >
          <template #default>
            <el-button size="small" type="warning" plain style="margin-top: 8px" @click="goRecharge">去充值</el-button>
          </template>
        </el-alert>
        <el-alert
          v-if="keyInfoError"
          type="error"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
          :title="keyInfoError"
        />

        <el-alert
          v-if="!keyInfo"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
          title="未保存有效 API Key：请先在顶部粘贴 API Key 并点【保存】，没有 Key 请点【申请】注册（新注册赠送 100 点）"
        />
        <el-alert
              type="info"
              :closable="false"
              show-icon
              style="margin-bottom: 12px"
              title="AI 剪辑即对话剪辑：导入源文件后，用一句话描述需求，AI 自动理解并执行。支持：滤镜（复古/黑白等16种）、抠图、画质增强、加文字水印（可指定方位）、裁剪/缩放/转格式、语音识别/合成。已上传图片还可做生成式修改（换装/加删物体/改背景/改画风，需配置 ModelScope Token）；未上传图片时说「生成/画一张…」可直接文生图。"
            />
            <div style="margin-bottom: 12px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap">
              <el-button type="primary" plain @click="pickMedia">导入源文件</el-button>
              <span v-if="attach" style="font-size: 13px; color: #67c23a">已导入：{{ attach.file.name }}</span>
              <el-link v-if="attach" type="danger" :underline="false" @click="attach = null">清除</el-link>
              <span v-else style="font-size: 12px; color: #909399">支持图片或音频，可从右侧按钮选择其他输入方式</span>
              <el-alert
                v-if="attach"
                type="success"
                :closable="false"
                show-icon
                style="flex-basis: 100%"
                title="附件已保留：继续发送指令将处理当前附件，换图请重新导入或点击清除"
              />
            </div>
            <div
              ref="chatBox"
              style="border: 1px solid #e4e7ed; border-radius: 8px; padding: 16px; min-height: 240px; max-height: 420px; overflow: auto"
            >
              <div v-if="messages.length === 0" style="color: #909399; font-size: 13px">
                例如：「给图片加水印」「转png格式」「抠图」「画质增强」「从5秒到20秒」「大声一点」「识别语音内容」「把这段文字转语音」。
              </div>
              <div v-for="(m, i) in messages" :key="i" style="margin-bottom: 12px">
                <div
                  :style="
                    m.role === 'user'
                      ? 'background:#ecf5ff; padding:8px 12px; border-radius:8px; display:inline-block; max-width:100%'
                      : 'background:#f4f4f5; padding:8px 12px; border-radius:8px; display:inline-block; max-width:100%'
                  "
                >
                  <b>{{ m.role === 'user' ? '我' : 'AI' }}：</b>{{ m.text }}
                </div>
                <div v-if="m.attachments" style="font-size: 12px; color: #909399; margin-top: 4px">{{ m.attachments }}</div>
                <img v-if="m.kind === 'image' && m.url" :src="m.url" style="max-width: 260px; margin-top: 8px; border: 1px solid #e4e7ed" />
                <div v-if="m.url && m.fname" style="margin-top: 8px; display: flex; gap: 8px">
                  <el-button size="small" @click="viewResult(m.url)">查看</el-button>
                  <el-button size="small" type="primary" plain @click="downloadResult(m.url, m.fname)">下载</el-button>
                </div>
                <audio v-if="m.kind === 'audio' && m.url" :src="m.url" controls style="width: 100%; margin-top: 8px" />
                <video v-if="m.kind === 'video' && m.url" :src="m.url" controls style="max-width: 400px; width: 100%; margin-top: 8px; border: 1px solid #e4e7ed" />
              </div>
            </div>
            <div style="display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; align-items: center">
              <el-input
                v-model="chatText"
                placeholder="输入文字指令，例如：给图片加水印"
                style="flex: 1; min-width: 220px"
                @keyup.enter="sendChat"
              />
              <el-button plain :type="isRecording ? 'danger' : ''" @click="toggleRecord">
                {{ isRecording ? '录音中，点击停止' : '语音' }}
              </el-button>
              <el-button plain @click="pickImage">图片</el-button>
              <el-button plain @click="pickMedia">文件</el-button>
              <el-button type="primary" :loading="chatLoading" @click="sendChat">发送</el-button>
            </div>
            <input ref="imageInput" type="file" accept="image/*" style="display: none" @change="onImage" />
            <input ref="mediaInput" type="file" accept="audio/*,image/*" style="display: none" @change="onMedia" />
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api'
import { onAuthChange } from '../../utils/auth'
import PortalNav from '../../components/PortalNav.vue'

const apiKey = ref(sessionStorage.getItem('api_key') || '')
const savingKey = ref(false)
const keyInfo = ref(null)
const keyInfoError = ref('')

const chatText = ref('')
const chatLoading = ref(false)
const chatBox = ref(null)
const messages = ref([])
const imageInput = ref(null)
const mediaInput = ref(null)
const attach = ref(null)
const isRecording = ref(false)
let recorder = null
let recStream = null
let recChunks = []
const attachMeta = computed(() => (attach.value ? `导入文件：${attach.value.file.name}` : ''))

onMounted(async () => {
  const hasLogin = !!localStorage.getItem('client_token')
  if (hasLogin) {
    try {
      const { data } = await http.get('/dev/client/me')
      if (data && data.api_key) {
        apiKey.value = data.api_key
        sessionStorage.setItem('api_key', data.api_key)
        await validateKey(true)
      }
    } catch (e) {
      // 会员会话失效时忽略，回退到本标签暂存的 Key
    }
  }
  const k = sessionStorage.getItem('api_key') || ''
  if (k) {
    apiKey.value = k
    await validateKey(true)
  }
})

function syncKeyFromAuth() {
  const token = localStorage.getItem('client_token')
  if (!token) {
    apiKey.value = sessionStorage.getItem('api_key') || ''
    validateKey(true)
  } else {
    http
      .get('/dev/client/me')
      .then(({ data }) => {
        if (data && data.api_key) {
          apiKey.value = data.api_key
          sessionStorage.setItem('api_key', data.api_key)
          validateKey(true)
        }
      })
      .catch(() => {})
  }
}

function onKeyStorage(e) {
  if (e.key !== 'api_key' && e.key !== 'saved_api_key' && e.key !== null) return
  syncKeyFromAuth()
}
window.addEventListener('storage', onKeyStorage)
const offAuth = onAuthChange(syncKeyFromAuth)
onUnmounted(() => {
  window.removeEventListener('storage', onKeyStorage)
  offAuth()
})

async function validateKey(silent) {
  const k = apiKey.value.trim()
  if (!k) {
    keyInfo.value = null
    if (!silent) keyInfoError.value = '请输入 API Key'
    return
  }
  try {
    const { data } = await http.get('/dev/key/info', { headers: { Authorization: `Bearer ${k}` } })
    keyInfo.value = data
    keyInfoError.value = ''
  } catch (e) {
    keyInfo.value = null
    keyInfoError.value = 'API Key 无效：' + (e.response?.data?.detail || '认证失败，请重新申请并保存')
  }
}

function copyKey() {
  const k = apiKey.value.trim()
  if (!k) return
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard
      .writeText(k)
      .then(() => ElMessage.success('Key 已复制，可粘贴分享给他人'))
      .catch(() => ElMessage.error('复制失败，请手动选择复制'))
  } else {
    ElMessage.error('当前浏览器不支持自动复制，请手动选择复制')
  }
}

function goRecharge() {
  location.href = localStorage.getItem('client_token') ? '/client/console' : '/client/login'
}

async function readErr(e) {
  const d = e?.response?.data
  if (d && typeof Blob !== 'undefined' && d instanceof Blob) {
    try {
      const t = await d.text()
      try {
        return JSON.parse(t).detail || t
      } catch {
        return t || null
      }
    } catch {
      return null
    }
  }
  return d?.detail || e?.message || ''
}

function clearKey() {
  localStorage.removeItem('api_key')
  localStorage.removeItem('saved_api_key')
  sessionStorage.removeItem('api_key')
  apiKey.value = ''
  keyInfo.value = null
  keyInfoError.value = ''
  ElMessage.success('已清除本机保存的 API Key')
}

async function saveKey() {
  const k = apiKey.value.trim()
  if (!k) return ElMessage.warning('请输入 API Key')
  savingKey.value = true
  try {
    const { data } = await http.get('/dev/key/info', { headers: { Authorization: `Bearer ${k}` } })
    sessionStorage.setItem('api_key', k)
    keyInfo.value = data
    keyInfoError.value = ''
    ElMessage.success(`Key 校验通过（${data.name}，余额 ${data.balance} 点），仅本标签会话记住`)
  } catch (e) {
    keyInfo.value = null
    keyInfoError.value = 'API Key 无效：' + (e.response?.data?.detail || '认证失败')
    ElMessage.error('API Key 无效，请重新申请或检查输入')
  } finally {
    savingKey.value = false
  }
}

function viewResult(url) {
  window.open(url, '_blank')
}

function downloadResult(url, name) {
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
}

async function toggleRecord() {
  if (isRecording.value) {
    recorder?.stop()
    return
  }
  try {
    recStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const mr = new MediaRecorder(recStream)
    recorder = mr
    recChunks = []
    mr.ondataavailable = (e) => {
      if (e.data && e.data.size) recChunks.push(e.data)
    }
    mr.onstop = () => {
      recStream.getTracks().forEach((t) => t.stop())
      const blob = new Blob(recChunks, { type: mr.mimeType || 'audio/webm' })
      if (blob.size) {
        attach.value = { type: 'voice', file: new File([blob], 'recording.webm', { type: blob.type }) }
        ElMessage.success('录音完成，可作为语音输入发送')
      } else {
        ElMessage.warning('录音为空，请重试')
      }
      isRecording.value = false
      recorder = null
    }
    mr.onerror = () => {
      isRecording.value = false
    }
    mr.start()
    isRecording.value = true
    ElMessage.info('开始录音，点击"停止"结束')
  } catch (e) {
    ElMessage.error('无法访问麦克风：' + (e.message || '请检查浏览器权限'))
  }
}

function pickImage() {
  imageInput.value.click()
}
function pickMedia() {
  mediaInput.value.click()
}
function onImage(e) {
  const f = e.target.files[0]
  if (f) attach.value = { type: 'media', file: f, kind: 'image' }
  e.target.value = ''
}
function onMedia(e) {
  const f = e.target.files[0]
  if (f) attach.value = { type: 'media', file: f, kind: f.type.startsWith('image') ? 'image' : 'audio' }
  e.target.value = ''
}

function scrollDown() {
  nextTick(() => {
    if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
  })
}

async function sendChat() {
  if (chatLoading.value) return
  if (!apiKey.value) return ElMessage.warning('请先填写并保存 API Key')
  const text = chatText.value.trim()
  const at = attach.value
  if (!text && !at) return ElMessage.warning('请导入源文件或输入指令')
  chatLoading.value = true
  messages.value.push({ role: 'user', text: text || '（语音/文件输入）', attachments: at ? attachMeta.value : '' })
  scrollDown()
  try {
    const form = new FormData()
    if (text) form.append('text', text)
    if (at?.type === 'voice') form.append('voice', at.file)
    if (at?.type === 'media') form.append('media', at.file)
    const headers = { Authorization: `Bearer ${apiKey.value}` }
    const submit = await http.post('/ai/chat', form, { headers, timeout: 180000 })
    const taskId = submit.data.task_id

    let out = null
    for (let i = 0; i < 420; i++) {
      await new Promise((r) => setTimeout(r, 1000))
      const poll = await http.get(`/tasks/${taskId}`, { headers, timeout: 20000 })
      if (poll.data.status === 'succeeded') {
        out = poll.data
        break
      }
      if (poll.data.status === 'failed') {
        messages.value.push({ role: 'assistant', text: '处理失败：' + (poll.data.error || '未知错误') })
        chatLoading.value = false
        chatText.value = ''
        scrollDown()
        return
      }
    }
    if (!out) {
      messages.value.push({ role: 'assistant', text: '处理仍在进行中，结果会保留，可在稍后刷新后查看控制台任务记录' })
      chatLoading.value = false
      chatText.value = ''
      scrollDown()
      return
    }

    const msg = { role: 'assistant', text: out.result_text || '处理完成' }
    if (out.result_url) {
      const name = out.result_url.split('/').pop()
      const fileResp = await http.get(`/result/${taskId}/${name}`, { headers, responseType: 'blob', timeout: 240000 })
      msg.kind = out.result_kind
      msg.fname = name
      msg.url = URL.createObjectURL(fileResp.data)
    }
    messages.value.push(msg)
  } catch (e) {
    const timedOut = e?.code === 'ECONNABORTED' || /timeout/i.test(e?.message || '')
    messages.value.push({
      role: 'assistant',
      text: timedOut
        ? '请求等待超时（长视频/大文件处理较慢）。任务仍在后台执行，可稍后在任务控制台查看结果，或改用较短视频时长。'
        : '提交失败：' + (e.response?.data?.detail || e.message || '未知错误')
    })
  } finally {
    chatLoading.value = false
    chatText.value = ''
    if (attach.value?.type === 'voice') attach.value = null
    scrollDown()
  }
}
</script>
