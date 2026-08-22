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
        title="填入 API Key 即可真实调用接口。没有 Key 请先到「申请 API Key」注册（新注册赠送 100 点）。"
      />

      <el-card>
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px">
          <b>API Key：</b>
          <el-input v-model="apiKey" placeholder="粘贴你的 API Key" style="max-width: 420px" show-password />
        </div>

        <el-tabs v-model="tab">
          <el-tab-pane label="图片剪辑" name="image">
            <el-form label-width="90px" style="max-width: 520px">
              <el-form-item label="上传图片">
                <input type="file" accept="image/*" @change="imgFile = $event.target.files[0]" />
              </el-form-item>
              <el-form-item label="滤镜">
                <el-select v-model="img.filter" style="width: 200px">
                  <el-option label="无" value="" />
                  <el-option label="灰度" value="gray" />
                  <el-option label="模糊" value="blur" />
                  <el-option label="锐化" value="sharpen" />
                  <el-option label="边缘" value="edge" />
                  <el-option label="浮雕" value="emboss" />
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
                <el-button type="primary" :loading="running" @click="runImage">开始剪辑</el-button>
              </el-form-item>
            </el-form>
            <div v-if="imgResult">
              <img :src="imgResult" style="max-width: 100%; max-height: 400px; border: 1px solid #e4e7ed" />
            </div>
          </el-tab-pane>

          <el-tab-pane label="音频剪辑" name="audio">
            <el-form label-width="90px" style="max-width: 520px">
              <el-form-item label="上传音频">
                <input type="file" accept="audio/*" @change="audFile = $event.target.files[0]" />
              </el-form-item>
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
                <el-button type="primary" :loading="running" @click="runAudio">开始剪辑</el-button>
              </el-form-item>
            </el-form>
            <div v-if="audResult">
              <audio :src="audResult" controls style="width: 100%" />
            </div>
          </el-tab-pane>

          <el-tab-pane label="AI 处理" name="ai">
            <el-form label-width="90px" style="max-width: 520px">
              <el-form-item label="任务类型">
                <el-select v-model="aiType" style="width: 200px">
                  <el-option label="人像抠图 (10点)" value="matting" />
                  <el-option label="画质增强 (15点)" value="enhance" />
                  <el-option label="语音识别 ASR (10点)" value="asr" />
                  <el-option label="语音合成 TTS (5点)" value="tts" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="aiType === 'tts'" label="合成文本">
                <el-input v-model="ttsText" placeholder="输入要合成语音的文本" />
              </el-form-item>
              <el-form-item v-else label="上传文件">
                <input
                  type="file"
                  :accept="aiType === 'asr' ? 'audio/*' : 'image/*'"
                  @change="aiFile = $event.target.files[0]"
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="running" @click="runAI">提交 AI 任务</el-button>
              </el-form-item>
            </el-form>
            <el-alert
              v-if="aiError"
              type="warning"
              :closable="false"
              :title="aiError"
              show-icon
              style="margin-top: 12px"
            />
            <div v-if="aiResultKind === 'image'" style="margin-top: 12px">
              <img :src="aiResultUrl" style="max-width: 100%; max-height: 400px; border: 1px solid #e4e7ed" />
            </div>
            <div v-if="aiResultKind === 'audio'" style="margin-top: 12px">
              <audio :src="aiResultUrl" controls style="width: 100%" />
            </div>
            <div v-if="aiResultKind === 'text'" style="margin-top: 12px">
              <el-card>识别结果：<b>{{ aiText }}</b></el-card>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api'
import PortalNav from '../../components/PortalNav.vue'

const apiKey = ref(localStorage.getItem('api_key') || '')
const tab = ref('image')
const running = ref(false)

const imgFile = ref(null)
const img = reactive({ filter: '', width: 0, watermark: '', format: '' })
const imgResult = ref('')

const audFile = ref(null)
const aud = reactive({ start: 0, end: 0, gain: 1, format: '' })
const audResult = ref('')

const aiType = ref('matting')
const aiFile = ref(null)
const ttsText = ref('')
const aiResultKind = ref('')
const aiResultUrl = ref('')
const aiText = ref('')
const aiError = ref('')

onMounted(() => {
  apiKey.value = localStorage.getItem('api_key') || ''
  const q = new URLSearchParams(location.search).get('tab')
  if (['image', 'audio', 'ai'].includes(q)) {
    tab.value = q
  }
})

function buildParams() {
  const params = {}
  if (img.filter) params.filter = img.filter
  if (img.width > 0) params.resize = { width: img.width }
  if (img.watermark) params.watermark = { text: img.watermark, position: [20, 20], size: 32, color: [255, 255, 255] }
  if (img.format) params.output_format = img.format
  return params
}

async function runImage() {
  if (!apiKey.value) return ElMessage.warning('请先填写 API Key')
  if (!imgFile.value) return ElMessage.warning('请选择图片文件')
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
  if (!apiKey.value) return ElMessage.warning('请先填写 API Key')
  if (!audFile.value) return ElMessage.warning('请选择音频文件')
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

async function runAI() {
  if (!apiKey.value) return ElMessage.warning('请先填写 API Key')
  if (aiType.value === 'tts') {
    if (!ttsText.value) return ElMessage.warning('请输入合成文本')
  } else if (!aiFile.value) {
    return ElMessage.warning('请选择文件')
  }
  running.value = true
  aiError.value = ''
  aiResultKind.value = ''
  try {
    const form = new FormData()
    if (aiType.value === 'tts') {
      form.append('text', ttsText.value)
    } else {
      form.append('file', aiFile.value)
    }
    const headers = { Authorization: `Bearer ${apiKey.value}` }
    const submit = await http.post(`/ai/${aiType.value}`, form, { headers })
    const taskId = submit.data.task_id

    for (let i = 0; i < 60; i++) {
      await new Promise((r) => setTimeout(r, 1000))
      const poll = await http.get(`/tasks/${taskId}`, { headers })
      const st = poll.data.status
      if (st === 'succeeded') {
        const name = poll.data.result_url.split('/').pop()
        const fileResp = await http.get(`/result/${taskId}/${name}`, { headers, responseType: 'blob' })
        const kind = fileResp.headers['content-type']
        if (kind.includes('image')) {
          aiResultKind.value = 'image'
          aiResultUrl.value = URL.createObjectURL(fileResp.data)
        } else if (kind.includes('audio')) {
          aiResultKind.value = 'audio'
          aiResultUrl.value = URL.createObjectURL(fileResp.data)
        } else {
          aiResultKind.value = 'text'
          aiText.value = await fileResp.data.text()
        }
        return
      }
      if (st === 'failed') {
        aiError.value = poll.data.error || '任务失败'
        return
      }
    }
    aiError.value = '任务超时，请稍后在控制台查看'
  } catch (e) {
    aiError.value = e.response?.data?.detail || 'AI 任务提交失败'
  } finally {
    running.value = false
  }
}
</script>
