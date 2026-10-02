<template>
  <div>
    <PortalNav />
    <div style="padding: 40px; max-width: 900px; margin: 0 auto">
      <h1 style="font-size: 22px; margin: 0 0 12px">MediaCut API 接入文档</h1>

      <h3>1. 认证</h3>
      <p>所有业务接口使用 <code>Authorization: Bearer &lt;API_KEY&gt;</code> 请求头认证。</p>

      <h3>2. 图片剪辑</h3>
      <pre>{{ imageExample }}</pre>

      <h3>3. 音频剪辑</h3>
      <pre>{{ audioExample }}</pre>

      <h3>4. AI 异步任务</h3>
      <pre>{{ aiExample }}</pre>

      <h3>5. AI 创作（文生图 / 图生图 / 文生视频）</h3>
      <pre>{{ createExample }}</pre>

      <h3>6. 错误码</h3>
      <el-table :data="errors" style="margin-top: 8px">
        <el-table-column prop="code" label="状态码" width="90" />
        <el-table-column prop="meaning" label="含义" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
import PortalNav from '../../components/PortalNav.vue'

const imageExample = `curl -X POST https://API_HOST/api/v1/image/edit \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "file=@photo.png" \\
  -F 'params={"resize": {"width": 800}, "filter": "gray", "output_format": "jpeg"}'`

const audioExample = `curl -X POST https://API_HOST/api/v1/audio/edit \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "file=@speech.wav" \\
  -F 'params={"crop": {"start": 1.5, "end": 10.0}, "output_format": "mp3"}'`

const aiExample = `# 提交任务
curl -X POST https://API_HOST/api/v1/ai/matting \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "file=@portrait.png"

# 响应: {"task_id": "...", "status": "pending", "status_url": "/api/v1/tasks/{task_id}"}

# 轮询状态
curl https://API_HOST/api/v1/tasks/{task_id} -H "Authorization: Bearer YOUR_API_KEY"`

const createExample = `# 文生图
curl -X POST https://API_HOST/api/v1/ai/t2i \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "prompt=赛博朋克城市夜景" -F "width=768" -F "height=768"

# 图生图编辑（multipart 上传原图 + 编辑描述）
curl -X POST https://API_HOST/api/v1/ai/i2i \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "file=@photo.png" -F "prompt=把背景换成海边日落"

# 文生视频（先生成画面，再添加镜头推拉/平移）
curl -X POST https://API_HOST/api/v1/ai/video \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "prompt=雪山湖泊，清晨薄雾" -F "duration=5" -F "motion=zoom"

# 语音合成
curl -X POST https://API_HOST/api/v1/ai/tts \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "text=欢迎使用 MediaCut" -F "voice=zh-CN-XiaoxiaoNeural"

# 语音识别（上传音频返回文本）
curl -X POST https://API_HOST/api/v1/ai/asr \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "file=@speech.mp3"

# 画质增强（上传图片）
curl -X POST https://API_HOST/api/v1/ai/enhance \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "file=@photo.png"

# 以上均为异步任务，提交后轮询 /api/v1/tasks/{task_id}
# 完成后用 GET /api/v1/result/{task_id}/{filename} 下载结果`

const errors = [
  { code: 401, meaning: 'API Key 无效' },
  { code: 402, meaning: '余额不足，请充值' },
  { code: 429, meaning: '当日配额已用完' },
  { code: 503, meaning: 'AI 模型未配置，请联系管理员' }
]
</script>

<style scoped>
pre {
  background: #f6f8fa;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.6;
}
code {
  background: #f6f8fa;
  padding: 2px 5px;
  border-radius: 4px;
}
</style>
