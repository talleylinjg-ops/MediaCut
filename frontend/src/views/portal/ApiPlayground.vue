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
          <span v-if="keyInfo" style="font-size: 12px; color: #67c23a">
            Key 有效：{{ keyInfo.name }}（余额 {{ keyInfo.balance }} 点）
          </span>
        </div>
        <el-alert
          v-if="keyInfoError"
          type="error"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
          :title="keyInfoError"
        />

        <el-tabs v-model="tab">
          <el-tab-pane label="图片剪辑" name="image">
            <div style="margin-bottom: 12px">
              <el-button type="primary" plain @click="imgPicker.click()">导入源文件</el-button>
              <span v-if="imgFile" style="margin-left: 12px; font-size: 13px; color: #67c23a">已导入：{{ imgFile.name }}</span>
              <input ref="imgPicker" type="file" accept="image/*" style="display: none" @change="onImgPick" />
            </div>
            <el-alert
              v-if="!keyInfo"
              type="warning"
              :closable="false"
              show-icon
              style="margin-bottom: 12px"
              title="未保存有效 API Key：请先在顶部粘贴 API Key 并点【保存】，没有 Key 请点【申请】注册（新注册赠送 100 点）"
            />
            <el-form label-width="90px" style="max-width: 520px">
              <el-form-item label="滤镜">
                <el-select v-model="img.filter" style="width: 200px">
                  <el-option label="无" value="" />
                  <el-option label="灰度" value="gray" />
                  <el-option label="模糊" value="blur" />
                  <el-option label="锐化" value="sharpen" />
                  <el-option label="边缘" value="edge" />
                  <el-option label="浮雕" value="emboss" />
                  <el-option label="电影色调" value="cinematic" />
                  <el-option label="反色" value="invert" />
                  <el-option label="棕褐复古" value="sepia" />
                  <el-option label="暖色调" value="warm" />
                  <el-option label="冷色调" value="cool" />
                  <el-option label="马赛克" value="pixelate" />
                  <el-option label="暗角" value="vignette" />
                  <el-option label="高对比" value="contrast" />
                  <el-option label="素描" value="sketch" />
                  <el-option label="卡通" value="cartoon" />
                  <el-option label="镜像" value="flip" />
                </el-select>
              </el-form-item>
              <el-form-item label="缩放宽度">
                <el-input-number v-model="img.width" :min="0" :max="4096" placeholder="0 表示不缩放" />
              </el-form-item>
              <el-form-item label="水印文本">
                <el-input v-model="img.watermark" placeholder="留空不加水印" />
              </el-form-item>
              <el-form-item label="输出格式">
                <el-select v-model="img.format" style="width: 200px">
                  <el-option label="保持原格式" value="" />
                  <el-option label="JPEG" value="jpeg" />
                  <el-option label="PNG" value="png" />
                  <el-option label="WEBP" value="webp" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :disabled="!keyInfo" :loading="running" @click="runImage">开始剪辑</el-button>
              </el-form-item>
            </el-form>
            <div v-if="imgResult">
              <img :src="imgResult" style="max-width: 100%; max-height: 400px; border: 1px solid #e4e7ed" />
              <div style="margin-top: 8px; display: flex; gap: 8px">
                <el-button size="small" @click="viewResult(imgResult)">查看</el-button>
                <el-button size="small" type="primary" plain @click="downloadResult(imgResult, 'edited-image.png')">下载</el-button>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="音频剪辑" name="audio">
            <div style="margin-bottom: 12px">
              <el-button type="primary" plain @click="audPicker.click()">导入源文件</el-button>
              <span v-if="audFile" style="margin-left: 12px; font-size: 13px; color: #67c23a">已导入：{{ audFile.name }}</span>
              <input ref="audPicker" type="file" accept="audio/*" style="display: none" @change="onAudPick" />
            </div>
            <el-alert
              v-if="!keyInfo"
              type="warning"
              :closable="false"
              show-icon
              style="margin-bottom: 12px"
              title="未保存有效 API Key：请先在顶部粘贴 API Key 并点【保存】，没有 Key 请点【申请】注册（新注册赠送 100 点）"
            />
            <el-form label-width="90px" style="max-width: 520px">
              <el-form-item label="裁剪起点 (s)">
                <el-input-number v-model="aud.start" :min="0" :step="0.5" />
              </el-form-item>
              <el-form-item label="裁剪终点 (s)">
                <el-input-number v-model="aud.end" :min="0" :step="0.5" placeholder="0 表示不裁剪" />
              </el-form-item>
              <el-form-item label="音量倍数">
                <el-input-number v-model="aud.gain" :min="0" :max="10" :step="0.1" />
              </el-form-item>
              <el-form-item label="输出格式">
                <el-select v-model="aud.format" style="width: 200px">
                  <el-option label="保持原格式" value="" />
                  <el-option label="MP3" value="mp3" />
                  <el-option label="WAV" value="wav" />
                  <el-option label="AAC" value="aac" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :disabled="!keyInfo" :loading="running" @click="runAudio">开始剪辑</el-button>
              </el-form-item>
            </el-form>
            <div v-if="audResult">
              <audio :src="audResult" controls style="width: 100%" />
              <div style="margin-top: 8px; display: flex; gap: 8px">
                <el-button size="small" @click="viewResult(audResult)">查看</el-button>
                <el-button size="small" type="primary" plain @click="downloadResult(audResult, 'edited-audio.wav')">下载</el-button>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="AI 剪辑" name="chat">
            <el-alert
              type="info"
              :closable="false"
              show-icon
              style="margin-bottom: 12px"
              title="AI 剪辑即对话剪辑：导入源文件后，用一句话描述需求，AI 自动理解并执行（抠图/增强/识别/合成/加水印/转格式等）。"
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
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api'
import PortalNav from '../../components/PortalNav.vue'

const apiKey = ref(sessionStorage.getItem('api_key') || '')
const tab = ref('image')
const running = ref(false)
const savingKey = ref(false)
const keyInfo = ref(null)
const keyInfoError = ref('')

const imgPicker = ref(null)
const imgFile = ref(null)
const img = reactive({ filter: '', width: 0, watermark: '', format: '' })
const imgResult = ref('')

const audPicker = ref(null)
const audFile = ref(null)
const aud = reactive({ start: 0, end: 0, gain: 1, format: '' })
const audResult = ref('')

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
  const k = sessionStorage.getItem('api_key')
  if (k) {
    apiKey.value = k
    await validateKey(true)
  }
  const q = new URLSearchParams(location.search).get('tab')
  if (['image', 'audio', 'chat'].includes(q)) {
    tab.value = q
  }
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

async function saveKey() {
  const k = apiKey.value.trim()
  if (!k) return ElMessage.warning('请输入 API Key')
  savingKey.value = true
  try {
    const { data } = await http.get('/dev/key/info', { headers: { Authorization: `Bearer ${k}` } })
    sessionStorage.setItem('api_key', k)
    keyInfo.value = data
    keyInfoError.value = ''
    ElMessage.success(`API Key 已保存并校验通过（${data.name}，余额 ${data.balance} 点）`)
  } catch (e) {
    keyInfo.value = null
    keyInfoError.value = 'API Key 无效：' + (e.response?.data?.detail || '认证失败')
    ElMessage.error('API Key 无效，请重新申请或检查输入')
  } finally {
    savingKey.value = false
  }
}

function onImgPick(e) {
  const f = e.target.files[0]
  if (f) imgFile.value = f
  e.target.value = ''
}

function onAudPick(e) {
  const f = e.target.files[0]
  if (f) audFile.value = f
  e.target.value = ''
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

function buildParams() {
  const params = {}
  if (img.filter) params.filter = img.filter
  if (img.width > 0) params.resize = { width: img.width }
  if (img.watermark) params.watermark = { text: img.watermark, position: [20, 20], size: 32, color: [255, 255, 255] }
  if (img.format) params.output_format = img.format
  return params
}

async function runImage() {
  if (!apiKey.value) return ElMessage.warning('请先填写并保存 API Key')
  if (!imgFile.value) return ElMessage.warning('请先导入源文件')
  running.value = true
  try {
    const form = new FormData()
    form.append('file', imgFile.value)
    form.append('params', JSON.stringify(buildParams()))
    const resp = await http.post('/image/edit', form, {
      headers: { Authorization: `Bearer ${apiKey.value}` },
      responseType: 'blob'
    })
    imgResult.value = URL.createObjectURL(resp.data)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '处理失败')
  } finally {
    running.value = false
  }
}

async function runAudio() {
  if (!apiKey.value) return ElMessage.warning('请先填写并保存 API Key')
  if (!audFile.value) return ElMessage.warning('请先导入源文件')
  running.value = true
  try {
    const params = {}
    if (aud.end > aud.start) params.crop = { start: aud.start, end: aud.end }
    if (aud.gain && aud.gain !== 1) params.volume = { gain: aud.gain }
    if (aud.format) params.output_format = aud.format
    const form = new FormData()
    form.append('file', audFile.value)
    form.append('params', JSON.stringify(params))
    const resp = await http.post('/audio/edit', form, {
      headers: { Authorization: `Bearer ${apiKey.value}` },
      responseType: 'blob'
    })
    audResult.value = URL.createObjectURL(resp.data)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '处理失败')
  } finally {
    running.value = false
  }
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
    const submit = await http.post('/ai/chat', form, { headers })
    const taskId = submit.data.task_id

    let out = null
    for (let i = 0; i < 90; i++) {
      await new Promise((r) => setTimeout(r, 1000))
      const poll = await http.get(`/tasks/${taskId}`, { headers })
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
      messages.value.push({ role: 'assistant', text: '处理超时，请稍后在控制台查看' })
      chatLoading.value = false
      chatText.value = ''
      scrollDown()
      return
    }

    const msg = { role: 'assistant', text: out.result_text || '处理完成' }
    if (out.result_url) {
      const name = out.result_url.split('/').pop()
      const fileResp = await http.get(`/result/${taskId}/${name}`, { headers, responseType: 'blob' })
      msg.kind = out.result_kind
      msg.fname = name
      msg.url = URL.createObjectURL(fileResp.data)
    }
    messages.value.push(msg)
  } catch (e) {
    messages.value.push({ role: 'assistant', text: '提交失败：' + (e.response?.data?.detail || e.message || '未知错误') })
  } finally {
    chatLoading.value = false
    chatText.value = ''
    if (attach.value?.type === 'voice') attach.value = null
    scrollDown()
  }
}
</script>
